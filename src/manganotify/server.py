from __future__ import annotations

import os
import json
import asyncio
import contextlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Annotated

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import mimetypes
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")



# ------------------------------------------------------------
# Env & Config
# ------------------------------------------------------------
load_dotenv()

BASE = os.getenv("MANGABAKA_BASE", "https://api.mangabaka.dev").rstrip("/")

DATA_DIR = Path(os.getenv("DATA_DIR", "./data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
WATCHLIST_PATH = DATA_DIR / "watchlist.json"
NOTIFY_PATH = DATA_DIR / "notifications.json"

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

def load_notifications() -> List[Dict[str, Any]]:
    if NOTIFY_PATH.exists():
        try:
            return json.loads(NOTIFY_PATH.read_text("utf-8"))
        except Exception:
            return []
    return []

def save_notifications(items: List[Dict[str, Any]]) -> None:
    # Keep compact; history can grow
    NOTIFY_PATH.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

def next_notification_id(items: List[Dict[str, Any]]) -> int:
    # simple monotonic int id
    try:
        return (max((int(x.get("id", 0)) for x in items), default=0) + 1)
    except Exception:
        return 1

def add_notification(kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload can include: series_id, title, old_total, new_total, unread, message, push_ok, etc.
    """
    items = load_notifications()
    rec = {
        "id": next_notification_id(items),
        "kind": kind,                       # "chapter_update" | "test" | ...
        "detected_at": now_utc_iso(),
        **payload
    }
    # newest first
    items.insert(0, rec)
    save_notifications(items)
    return rec


# ------------------------------------------------------------
# Coercion helpers
# ------------------------------------------------------------
def to_int(v: Any) -> Optional[int]:
    if v is None:
        return None
    try:
        # strings like "94", "94.0" → 94
        s = str(v).strip()
        if s == "":
            return None
        if "." in s:
            return int(float(s))
        return int(s)
    except Exception:
        return None


def to_bool_or_none(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"1", "true", "yes", "on"}:
        return True
    if s in {"0", "false", "no", "off"}:
        return False
    return None


def str_eq(a: Any, b: Optional[str]) -> bool:
    if b is None or b == "":
        return True
    return (a is not None) and (str(a).lower() == str(b).lower())


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


async def api_series_by_id(client: httpx.AsyncClient, series_id: int | str, *, full: bool = False) -> Dict[str, Any]:
    url = f"{BASE}/v1/series/{series_id}" + ("/full" if full else "")
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
            data={"token": PUSHOVER_APP_TOKEN, "user": PUSHOVER_USER_KEY, "title": title, "message": message},
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
# Data shaping
# ------------------------------------------------------------
def pick_cover(series: Dict[str, Any]) -> Optional[str]:
    cov = series.get("cover") or {}
    return cov.get("small") or cov.get("default") or cov.get("raw")


def derive_last_chapter_at(series_full: Dict[str, Any]) -> Optional[str]:
    """
    Try to surface some notion of 'last chapter updated at'.
    Prefer series.last_updated_at, else try per-source timestamps if present.
    """
    if series_full.get("last_updated_at"):
        return series_full["last_updated_at"]
    src = series_full.get("source") or {}
    # try some well-known sources
    for k in ("anilist", "my_anime_list", "anime_news_network", "manga_updates", "kitsu", "shikimori", "mangadex"):
        s = src.get(k) or {}
        ts = s.get("last_updated_at")
        if ts:
            return ts
    return None


def normalize_series_min(series: Dict[str, Any]) -> Dict[str, Any]:
    """Flatten common fields used by UI from either /search items or /full data.data."""
    return {
        "id": series.get("id"),
        "title": series.get("title"),
        "total_chapters": to_int(series.get("total_chapters")),
        "has_anime": bool(series.get("has_anime")) if series.get("has_anime") is not None else None,
        "status": series.get("status"),
        "type": series.get("type"),
        "content_rating": series.get("content_rating"),
        "cover": pick_cover(series),
        "last_updated_at": series.get("last_updated_at"),
        "state": series.get("state"),
        "merged_with": series.get("merged_with"),
    }


# ------------------------------------------------------------
# Background Poller
# ------------------------------------------------------------
async def poll_watchlist_loop(app: FastAPI) -> None:
    """
    Periodically refresh chapter counts and send Pushover if increased.
    Handles merged series by auto-updating IDs.
    """
    client: httpx.AsyncClient = app.state.client
    interval = max(POLL_INTERVAL_SEC, 0)

    while interval > 0:
        try:
            wl = load_watchlist()
            changed = False

            for item in wl:
                sid = item.get("id")
                if not sid:
                    continue

                try:
                    data = await api_series_by_id(client, sid, full=True)
                    series = data.get("data") or data

                    # Handle merges
                    if str(series.get("state")) == "merged" and series.get("merged_with"):
                        item["id"] = series["merged_with"]
                        # fetch the new series to refresh
                        data = await api_series_by_id(client, item["id"], full=True)
                        series = data.get("data") or data

                    new_total = to_int(series.get("total_chapters"))
                    old_total = to_int(item.get("total_chapters"))
                    last_read = to_int(item.get("last_read")) or 0

                    if new_total is not None and old_total is not None and new_total > old_total:
                        unread = max(new_total - last_read, 0)
                        msg = f"{item.get('title', '(unknown)')} now has {new_total} chapters."
                        if unread > 0:
                            msg += f" You’re {unread} behind."

                        push_res = await app.state.push_func(
                            client,
                            title=f"New chapter(s): {item.get('title', '(unknown)')}",
                            message=msg,
                        )

                        # record history
                        add_notification(
                            "chapter_update",
                            {
                                "series_id": item.get("id"),
                                "title": item.get("title"),
                                "old_total": old_total,
                                "new_total": new_total,
                                "unread": unread,
                                "message": msg,
                                "push_ok": bool(getattr(push_res, "get", lambda _: False)("ok") if isinstance(push_res,
                                                                                                              dict) else False),
                            },
                        )

                    # Update stored info
                    item["title"] = series.get("title") or item.get("title")
                    if new_total is not None:
                        item["total_chapters"] = new_total
                    cov = pick_cover(series)
                    if cov:
                        item["cover"] = cov
                    item["last_chapter_at"] = derive_last_chapter_at(series)
                    item["last_checked"] = now_utc_iso()
                    changed = True
                except Exception:
                    # swallow per-item errors
                    continue

            if changed:
                save_watchlist(wl)
        except Exception:
            # swallow entire-loop iteration errors
            pass

        await asyncio.sleep(interval)


# ------------------------------------------------------------
# One-shot processor (handy for tests)
# ------------------------------------------------------------
async def process_watchlist_once(app: FastAPI, *, now: Optional[datetime] = None) -> dict:
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
            data = await api_series_by_id(client, sid, full=True)
            series = data.get("data") or data

            # merges
            if str(series.get("state")) == "merged" and series.get("merged_with"):
                item["id"] = series["merged_with"]
                data = await api_series_by_id(client, item["id"], full=True)
                series = data.get("data") or data

            new_total = to_int(series.get("total_chapters"))
            old_total = to_int(item.get("total_chapters"))

            if new_total is not None and old_total is not None and new_total > old_total:
                res = await push(
                    client,
                    title=f"New chapter(s): {item.get('title', '(unknown)')}",
                    message=f"{item.get('title', '(unknown)')} has {new_total} chapters (was {old_total}).",
                )
                if isinstance(res, dict) and res.get("ok"):
                    notified += 1

                add_notification(
                    "chapter_update",
                    {
                        "series_id": item.get("id"),
                        "title": item.get("title"),
                        "old_total": old_total,
                        "new_total": new_total,
                        "unread": max((new_total or 0) - (to_int(item.get('last_read')) or 0), 0),
                        "message": f"{item.get('title', '(unknown)')} has {new_total} chapters (was {old_total}).",
                        "push_ok": bool(res.get("ok")) if isinstance(res, dict) else False,
                    },
                )

            # store freshest values
            item["title"] = series.get("title") or item.get("title")
            if new_total is not None:
                item["total_chapters"] = new_total
            cov = pick_cover(series)
            if cov:
                item["cover"] = cov
            item["last_chapter_at"] = derive_last_chapter_at(series)

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

    # Disabled old poller - using new poller system in main.py instead
    # if POLL_INTERVAL_SEC > 0:
    #     app.state.poller_task = asyncio.create_task(poll_watchlist_loop(app))

    try:
        yield
    finally:
        if app.state.poller_task:
            app.state.poller_task.cancel()
            with contextlib.suppress(Exception):
                await app.state.poller_task
        await app.state.client.aclose()


app = FastAPI(title="MangaNotify", version="0.3", lifespan=lifespan)

from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Static SPA
app.mount("/static", StaticFiles(directory=str(ASSETS_DIR / "static")), name="static")


@app.get("/")
async def index():
    return FileResponse(str(ASSETS_DIR / "static" / "index.html"))


# images (favicons etc.)
app.mount("/images", StaticFiles(directory=str(ASSETS_DIR / "static" / "images")), name="images")


@app.get("/favicon.ico")
async def favicon():
    return FileResponse(str(ASSETS_DIR / "static" / "images" / "favicon-32.png"))


# ------------------------------------------------------------
# API: Search & Series
# ------------------------------------------------------------
@app.get("/api/search")
async def search_endpoint(
    request: Request,
    q: Annotated[str, Query(min_length=1)],
    page: int = 1,
    limit: int = 50,
    # Optional client-side filters we WON'T forward upstream
    status: Optional[str] = Query(None, description="publication status"),
    type: Optional[str] = Query(None, description="media type"),
    content_rating: Optional[str] = Query(None, description="content rating"),
    has_anime: Optional[str | bool] = Query(None, description="boolean-like"),
):
    """
    We only pass q/page/limit to upstream. Optional filters are applied locally
    to avoid 400 errors from unsupported upstream params.
    """
    try:
        raw = await api_search(request.app.state.client, q, page=page, limit=limit)
        items = raw.get("data") or raw.get("results") or []
        items = [normalize_series_min(it) for it in items]

        want_has_anime = to_bool_or_none(has_anime)

        def keep(it: dict) -> bool:
            if not str_eq(it.get("status"), status):
                return False
            if not str_eq(it.get("type"), type):
                return False
            if not str_eq(it.get("content_rating"), content_rating):
                return False
            if want_has_anime is not None:
                v = to_bool_or_none(it.get("has_anime"))
                if v is None or v is not want_has_anime:
                    return False
            return True

        filtered = [it for it in items if keep(it)]

        out = dict(raw)
        out["data"] = filtered
        if "pagination" in out and isinstance(out["pagination"], dict):
            out["pagination"]["count"] = len(filtered)
        return out

    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, str(e))
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")


@app.get("/api/series/{series_id}")
async def series_endpoint(request: Request, series_id: int, full: bool = True):
    """
    Returns upstream /v1/series/{id}/full by default (full=True), but you can
    pass ?full=false to get the slim version if you need it.
    Also normalizes a few fields at top-level for convenience.
    """
    try:
        data = await api_series_by_id(request.app.state.client, series_id, full=bool(full))
        series = data.get("data") or data

        # If merged, surface that clearly so callers can follow up
        merged_target = series.get("merged_with") if str(series.get("state")) == "merged" else None

        minimal = normalize_series_min(series)
        # include a couple more hints for the UI
        minimal["last_chapter_at"] = derive_last_chapter_at(series)

        return {"status": 200, "data": series, "minimal": minimal, "merged_with": merged_target}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Lookup failed: {e}")


# ------------------------------------------------------------
# API: Watchlist
# ------------------------------------------------------------
@app.get("/api/watchlist")
def get_watchlist():
    items = load_watchlist()
    out: List[Dict[str, Any]] = []

    for it in items:
        total = to_int(it.get("total_chapters")) or 0
        last_read = to_int(it.get("last_read")) or 0
        unread = max(total - last_read, 0)
        out.append(
            {
                **it,
                "total_chapters": total or None,
                "last_read": last_read or 0,
                "unread": unread,
                "is_behind": unread > 0,
            }
        )
    return {"data": out}


@app.post("/api/watchlist")
async def add_watchlist(item: Dict[str, Any], request: Request):
    """
    Accepts {id, title?, total_chapters?, last_read?}. We enrich from /full.
    - If series is merged, we store the new ID transparently.
    - We store cover + last_chapter_at for UI.
    """
    if "id" not in item:
        raise HTTPException(400, "Missing 'id'")

    wl = load_watchlist()
    sid = str(item["id"])
    if any(str(x.get("id")) == sid for x in wl):
        return {"ok": True, "message": "Already in watchlist"}

    # Hydrate from /full
    try:
        data = await api_series_by_id(request.app.state.client, sid, full=True)
        series = data.get("data") or data
        # handle merged
        if str(series.get("state")) == "merged" and series.get("merged_with"):
            sid = str(series["merged_with"])
            data = await api_series_by_id(request.app.state.client, sid, full=True)
            series = data.get("data") or data
    except Exception:
        series = {}

    total = to_int(item.get("total_chapters"))
    if total is None:
        total = to_int(series.get("total_chapters"))

    cov = pick_cover(series) if series else None
    last_chapter_at = derive_last_chapter_at(series) if series else None

    record = {
        "id": int(sid),
        "title": item.get("title") or series.get("title"),
        "total_chapters": total,
        "last_read": to_int(item.get("last_read")) or 0,
        "cover": cov,
        "added_at": now_utc_iso(),
        "last_chapter_at": last_chapter_at,
        "last_checked": now_utc_iso(),
    }
    wl.append(record)
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
    body supports:
      - {"mark_latest": true}
      - {"last_read": 123}
      - {"decrement": 1}  # decrease last_read by 1, >= 0
    """
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            total = to_int(it.get("total_chapters"))
            last = to_int(it.get("last_read")) or 0

            if body.get("mark_latest"):
                it["last_read"] = total if total is not None else last
            elif "decrement" in body:
                step = to_int(body.get("decrement")) or 1
                it["last_read"] = max(0, last - step)
            elif "last_read" in body:
                lr = to_int(body.get("last_read"))
                if lr is None:
                    raise HTTPException(400, "last_read must be an integer")
                it["last_read"] = max(0, lr)
            else:
                raise HTTPException(400, "No recognized progress action")

            it["last_checked"] = now_utc_iso()
            save_watchlist(wl)
            return {"ok": True, "last_read": it["last_read"]}

    raise HTTPException(404, "Not in watchlist")


@app.post("/api/watchlist/{series_id}/read/next")
async def mark_next(series_id: int):
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            lr = to_int(it.get("last_read")) or 0
            it["last_read"] = lr + 1
            it["last_checked"] = now_utc_iso()
            save_watchlist(wl)
            return {"ok": True, "last_read": it["last_read"]}
    raise HTTPException(404, "Not in watchlist")

@app.post("/api/watchlist/refresh")
async def trigger_refresh(request: Request):
    # Run the new poller's process_once function and return counts
    from .services.poller import process_once
    stats = await process_once(request.app)
    return stats

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
    if not PUSHOVER_APP_TOKEN or not PUSHOVER_USER_KEY:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "Missing Pushover env vars",
                "expected_env": ["PUSHOVER_APP_TOKEN", "PUSHOVER_USER_KEY"],
            },
        )

    client: httpx.AsyncClient = request.app.state.client
    result = await pushover(client, "MangaNotify", "✅ MangaNotify test notification")
    status = 200 if result.get("ok") else 502

    result["who"] = {"token": env_mask(PUSHOVER_APP_TOKEN), "user": env_mask(PUSHOVER_USER_KEY)}
    # record test entry regardless of push success so users see it in history
    add_notification(
        "test",
        {
            "title": "MangaNotify test",
            "message": "Manual test notification",
            "push_ok": bool(result.get("ok")),
        },
    )
    return JSONResponse(status_code=status, content=result)

@app.get("/api/notifications")
def list_notifications(limit: int = 200):
    items = load_notifications()
    return {"data": items[: max(1, min(limit, 1000))]}

@app.delete("/api/notifications/{nid}")
def delete_notification(nid: int):
    items = load_notifications()
    before = len(items)
    items = [x for x in items if int(x.get("id", -1)) != int(nid)]
    save_notifications(items)
    return {"removed": before - len(items)}

@app.delete("/api/notifications")
def clear_notifications():
    save_notifications([])
    return {"removed": "all"}


app.include_router(router)


# ------------------------------------------------------------
# Local dev entrypoint (optional)
# ------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    import pathlib

    os.chdir(pathlib.Path(__file__).parent)
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8999")), reload=False)
