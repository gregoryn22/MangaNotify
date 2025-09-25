# src/manganotify/server.py
from __future__ import annotations

import os
import json
import asyncio
import contextlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ------------------------------------------------------------
# Env & Config
# ------------------------------------------------------------
load_dotenv()  # loads .env if present

BASE = os.getenv("MANGABAKA_BASE", "https://api.mangabaka.dev").rstrip("/")

# Keep data directory outside the package by default; override via env.
DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
WATCHLIST_PATH = DATA_DIR / "watchlist.json"

# Pushover (optional)
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY") or os.getenv("PUSHOVER_USER")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN") or os.getenv("PUSHOVER_TOKEN")

# Poll every N seconds (0 or negative disables background checks)
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "1800"))

# Where our bundled static files live (inside the package dir)
ASSETS_DIR = Path(__file__).parent


def now_utc_iso() -> str:
    """RFC3339 / ISO 8601 UTC with trailing Z."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ------------------------------------------------------------
# Persistence helpers
# ------------------------------------------------------------
def load_watchlist() -> List[Dict[str, Any]]:
    if WATCHLIST_PATH.exists():
        try:
            return json.loads(WATCHLIST_PATH.read_text("utf-8"))
        except Exception:
            return []
    return []


def save_watchlist(items: List[Dict[str, Any]]) -> None:
    WATCHLIST_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")


# ------------------------------------------------------------
# Upstream API wrappers (use app.state.client)
# ------------------------------------------------------------
async def api_search(
    client: httpx.AsyncClient, q: str, page: int = 1, limit: int = 50
) -> Dict[str, Any]:
    url = f"{BASE}/v1/series/search"
    r = await client.get(url, params={"q": q, "page": page, "limit": min(limit, 50)})
    r.raise_for_status()
    return r.json()


async def api_series_by_id(client: httpx.AsyncClient, series_id: int | str) -> Dict[str, Any]:
    url = f"{BASE}/v1/series/{series_id}"
    r = await client.get(url)
    if r.status_code == 404:
        raise HTTPException(404, "Series not found")
    r.raise_for_status()
    return r.json()


# ------------------------------------------------------------
# Pushover
# ------------------------------------------------------------
def env_mask(s: Optional[str], keep: int = 4) -> str:
    if not s:
        return ""
    return (s[:keep] + "…") if len(s) > keep else "…"


async def pushover(client: httpx.AsyncClient, title: str, message: str) -> Dict[str, Any]:
    """
    Send a Pushover notification. Returns dict with ok/bodies for UI diagnostics.
    Does nothing (but returns ok=False + reason) if env vars are missing.
    """
    if not PUSHOVER_APP_TOKEN or not PUSHOVER_USER_KEY:
        return {"ok": False, "reason": "Missing PUSHOVER_* envs"}

    try:
        r = await client.post(
            "https://api.pushover.net/1/messages.json",
            data={
                "token": PUSHOVER_APP_TOKEN,
                "user": PUSHOVER_USER_KEY,
                "title": title,
                "message": message,
            },
            timeout=15.0,
        )
        try:
            js = r.json()
        except Exception:
            js = {"raw": await r.aread()}

        ok = (r.status_code == 200) and (js.get("status") == 1)
        return {
            "ok": ok,
            "http_status": r.status_code,
            "pushover_status": js.get("status"),
            "errors": js.get("errors"),
            "request_id": js.get("request"),
        }
    except httpx.RequestError as e:
        return {"ok": False, "reason": f"Network error: {e!s}"}


# ------------------------------------------------------------
# Background Poller
# ------------------------------------------------------------
async def poll_watchlist_loop(app: FastAPI) -> None:
    """
    Periodically refresh chapter counts and send Pushover if increased.
    Never raises; logs are minimal to keep container noise low.
    """
    client: httpx.AsyncClient = app.state.client
    interval = max(POLL_INTERVAL_SEC, 0)

    while interval > 0:
        try:
            wl = load_watchlist()
            something_changed = False

            for item in wl:
                sid = item.get("id")
                if not sid:
                    continue

                try:
                    data = await api_series_by_id(client, sid)
                    series = data.get("data") or data

                    # Normalize total_chapters to int
                    def to_int(v):
                        try:
                            return int(v) if v is not None else None
                        except Exception:
                            return None

                    new_total = to_int(series.get("total_chapters"))
                    old_total = to_int(item.get("total_chapters"))

                    # inside poll/process loop after fetching series:
                    new_total = to_int(series.get("total_chapters"))
                    old_total = to_int(item.get("total_chapters"))
                    last_read = to_int(item.get("last_read")) or 0

                    if (new_total is not None) and (old_total is not None) and new_total > old_total:
                        unread = max(new_total - last_read, 0)
                        msg = f"{item.get('title', '(unknown)')} now has {new_total} chapters."
                        if unread > 0:
                            msg += f" You’re {unread} behind."
                        await pushover(client, title=f"New chapter(s): {item.get('title', '(unknown)')}", message=msg)
                    # Update stored info
                    item["title"] = series.get("title") or item.get("title")
                    if new_total is not None:
                        item["total_chapters"] = new_total
                    item["last_checked"] = now_utc_iso()
                    something_changed = True

                except Exception:
                    # swallow per-item errors
                    continue

            if something_changed:
                save_watchlist(wl)
        except Exception:
            # swallow entire-loop iteration errors
            pass

        await asyncio.sleep(interval)


async def process_watchlist_once(app: FastAPI, *, now: Optional[datetime] = None) -> dict:
    """
    Single iteration of the watchlist check.
    Returns dict with summary for tests:
      {"checked": N, "updated": M, "notified": K}
    """
    client: httpx.AsyncClient = app.state.client
    push = getattr(app.state, "push_func", pushover)

    wl = load_watchlist()
    checked = updated = notified = 0

    for item in wl:
        sid = item.get("id")
        if not sid:
            continue
        checked += 1
        try:
            data = await api_series_by_id(client, sid)
            series = data.get("data") or data

            def to_int(v):
                try:
                    return int(v) if v is not None else None
                except Exception:
                    return None

            new_total = to_int(series.get("total_chapters"))
            old_total = to_int(item.get("total_chapters"))

            if new_total is not None and old_total is not None and new_total > old_total:
                res = await push(
                    client,
                    title=f"New chapter(s): {item.get('title','(unknown)')}",
                    message=f"{item.get('title','(unknown)')} has {new_total} chapters (was {old_total}).",
                )
                if isinstance(res, dict) and res.get("ok"):
                    notified += 1

            # store freshest values
            item["title"] = series.get("title") or item.get("title")
            if new_total is not None:
                item["total_chapters"] = new_total

            now_dt = now or datetime.now(timezone.utc)
            item["last_checked"] = now_dt.isoformat().replace("+00:00", "Z")
            updated += 1
        except Exception:
            continue

    if updated:
        save_watchlist(wl)

    return {"checked": checked, "updated": updated, "notified": notified}


# ------------------------------------------------------------
# Lifespan & App
# ------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.client = httpx.AsyncClient(timeout=20.0)
    app.state.poller_task = None
    app.state.push_func = pushover  # allow tests to override

    if POLL_INTERVAL_SEC > 0:
        app.state.poller_task = asyncio.create_task(poll_watchlist_loop(app))

    try:
        yield
    finally:
        if app.state.poller_task:
            app.state.poller_task.cancel()
            with contextlib.suppress(Exception):
                await app.state.poller_task
        await app.state.client.aclose()


app = FastAPI(title="MangaNotify", version="0.2", lifespan=lifespan)

# Static SPA (fix: use leading slash and package-relative directory)
app.mount("/static", StaticFiles(directory=str(ASSETS_DIR / "static")), name="static")


@app.get("/")
async def index():
    return FileResponse(str(ASSETS_DIR / "static" / "index.html"))


# ------------------------------------------------------------
# API: Search & Series
# ------------------------------------------------------------
@app.get("/api/search")
async def search_endpoint(
    request: Request,
    q: str = Query(..., min_length=1),
    page: int = 1,
    limit: int = 50,
):
    try:
        return await api_search(request.app.state.client, q, page=page, limit=limit)
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, str(e))
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")


@app.get("/api/series/{series_id}")
async def series_endpoint(request: Request, series_id: int):
    try:
        return await api_series_by_id(request.app.state.client, series_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Lookup failed: {e}")


# ------------------------------------------------------------
# API: Watchlist
# ------------------------------------------------------------
def to_int(v):
    try:
        return int(v) if v is not None else None
    except Exception:
        return None

@app.get("/api/watchlist")
def get_watchlist():
    items = load_watchlist()
    out = []
    for it in items:
        total = to_int(it.get("total_chapters")) or 0
        last_read = to_int(it.get("last_read")) or 0
        unread = max(total - last_read, 0)
        out.append({**it, "unread": unread, "is_behind": unread > 0})
    return {"data": out}


@app.post("/api/watchlist")
async def add_watchlist(item: Dict[str, Any]):
    """
    expects: {"id": 377, "title": "...", "total_chapters": 1160}
    """
    if "id" not in item:
        raise HTTPException(400, "Missing 'id'")

    wl = load_watchlist()
    sid = str(item["id"])
    if any(str(x.get("id")) == sid for x in wl):
        return {"ok": True, "message": "Already in watchlist"}

    try:
        total = int(item.get("total_chapters")) if item.get("total_chapters") is not None else None
    except Exception:
        total = item.get("total_chapters")

    wl.append(
        {
            "id": item["id"],
            "title": item.get("title"),
            "total_chapters": total,
            "added_at": now_utc_iso(),
        }
    )
    save_watchlist(wl)
    return {"ok": True}


@app.delete("/api/watchlist/{series_id}")
async def remove_watchlist(series_id: int):
    wl = load_watchlist()
    before = len(wl)
    wl = [x for x in wl if str(x.get("id")) != str(series_id)]
    save_watchlist(wl)
    return {"removed": before - len(wl)}

@app.patch("/api/watchlist/{series_id}/progress")
async def set_progress(series_id: int, body: Dict[str, Any]):
    """
    body: {"last_read": 123} or {"mark_latest": true}
    """
    wl = load_watchlist()
    found = False
    for it in wl:
        if str(it.get("id")) == str(series_id):
            found = True
            if body.get("mark_latest"):
                # snap to current known total
                total = it.get("total_chapters")
                try:
                    it["last_read"] = int(total) if total is not None else None
                except Exception:
                    it["last_read"] = None
            else:
                # explicit chapter number
                lr = body.get("last_read")
                try:
                    it["last_read"] = int(lr) if lr is not None else None
                except Exception:
                    raise HTTPException(400, "last_read must be an integer")
            break
    if not found:
        raise HTTPException(404, "Not in watchlist")

    save_watchlist(wl)
    return {"ok": True}

@app.post("/api/watchlist/{series_id}/read/next")
async def mark_next(series_id: int):
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            lr = to_int(it.get("last_read")) or 0
            it["last_read"] = lr + 1
            save_watchlist(wl)
            return {"ok": True, "last_read": it["last_read"]}
    raise HTTPException(404, "Not in watchlist")

@app.post("/api/watchlist")
async def add_watchlist(item: Dict[str, Any]):
    ...
    try:
        total = int(item.get("total_chapters")) if item.get("total_chapters") is not None else None
    except Exception:
        total = item.get("total_chapters")

    wl.append({
        "id": item["id"],
        "title": item.get("title"),
        "total_chapters": total,
        "last_read": total,            # <— initialize progress
        "added_at": now_utc_iso(),
    })
    save_watchlist(wl)
    return {"ok": True}


# ------------------------------------------------------------
# API: Health & Notifications
# ------------------------------------------------------------
router = APIRouter()


@router.get("/api/health")
def health():
    return {"ok": True}


@router.get("/api/notify/debug")
def notify_debug():
    return {
        "has_token": bool(PUSHOVER_APP_TOKEN),
        "has_user": bool(PUSHOVER_USER_KEY),
        "token_preview": env_mask(PUSHOVER_APP_TOKEN),
        "user_preview": env_mask(PUSHOVER_USER_KEY),
        "notes": "Both must be True for notifications to work.",
    }


@router.post("/api/notify/test")
async def notify_test(request: Request):
    # gate early if creds missing
    if not PUSHOVER_APP_TOKEN or not PUSHOVER_USER_KEY:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "Missing Pushover env vars",
                "expected_env": ["PUSHOVER_APP_TOKEN", "PUSHOVER_USER_KEY"],
            },
        )

    # safe to use client now
    client: httpx.AsyncClient = request.app.state.client
    result = await pushover(client, "MangaNotify", "✅ MangaNotify test notification")
    status = 200 if result.get("ok") else 502

    # add masked who block
    result["who"] = {
        "token": env_mask(PUSHOVER_APP_TOKEN),
        "user": env_mask(PUSHOVER_USER_KEY),
    }
    return JSONResponse(status_code=status, content=result)


app.include_router(router)


# ------------------------------------------------------------
# Local dev entrypoint (optional)
# ------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    import pathlib

    # Ensure relative static paths work even when IDE changes CWD
    os.chdir(pathlib.Path(__file__).parent)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8999")),
        reload=False,
    )
