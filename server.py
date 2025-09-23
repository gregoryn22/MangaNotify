# server.py
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import requests
from fastapi import FastAPI, HTTPException, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

# ---------- Config ----------
BASE = os.getenv("MANGABAKA_BASE", "https://api.mangabaka.dev").rstrip("/")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
WATCHLIST_PATH = DATA_DIR / "watchlist.json"

# Pushover (optional)
PUSHOVER_USER_KEY = os.getenv("PUSHOVER_USER_KEY") or os.getenv("PUSHOVER_USER")
PUSHOVER_APP_TOKEN = os.getenv("PUSHOVER_APP_TOKEN") or os.getenv("PUSHOVER_TOKEN")
POLL_INTERVAL_SEC = int(os.getenv("POLL_INTERVAL_SEC", "1800"))  # 30 min default

# ---------- Simple persistence ----------
def load_watchlist() -> List[Dict[str, Any]]:
    if WATCHLIST_PATH.exists():
        try:
            return json.loads(WATCHLIST_PATH.read_text("utf-8"))
        except Exception:
            return []
    return []

def save_watchlist(items: List[Dict[str, Any]]) -> None:
    WATCHLIST_PATH.write_text(json.dumps(items, indent=2), encoding="utf-8")

# ---------- Upstream HTTP client ----------
client = httpx.AsyncClient(timeout=20.0)

async def api_search(q: str, page: int = 1, limit: int = 50) -> Dict[str, Any]:
    url = f"{BASE}/v1/series/search"
    r = await client.get(url, params={"q": q, "page": page, "limit": min(max(limit, 1), 50)})
    r.raise_for_status()
    return r.json()

async def api_series_by_id(series_id: int | str) -> Dict[str, Any]:
    url = f"{BASE}/v1/series/{series_id}"
    r = await client.get(url)
    if r.status_code == 404:
        raise HTTPException(404, "Series not found")
    r.raise_for_status()
    return r.json()

# ---------- Pushover ----------
async def pushover(title: str, message: str) -> None:
    """Fire-and-forget push (errors are swallowed)."""
    if not (PUSHOVER_USER_KEY and PUSHOVER_APP_TOKEN):
        return
    try:
        await client.post(
            "https://api.pushover.net/1/messages.json",
            data={"token": PUSHOVER_APP_TOKEN, "user": PUSHOVER_USER_KEY, "title": title, "message": message},
        )
    except Exception:
        pass

# ---------- Background poller ----------
poller_task: Optional[asyncio.Task] = None

async def poll_watchlist_loop():
    while True:
        try:
            wl = load_watchlist()
            updated_any = False
            for item in wl:
                sid = item.get("id")
                if not sid:
                    continue
                try:
                    data = await api_series_by_id(sid)
                    series = data.get("data") or data  # handle both wrapped/plain
                    # normalize totals (API may return string)
                    def to_int(v):
                        try:
                            return int(v) if v is not None else None
                        except (TypeError, ValueError):
                            return None

                    new_total = to_int(series.get("total_chapters"))
                    old_total = to_int(item.get("total_chapters"))

                    if new_total is not None and old_total is not None and new_total > old_total:
                        await pushover(
                            title=f"New chapter(s): {item.get('title','(unknown)')}",
                            message=f"{item.get('title','(unknown)')} has {new_total} chapters (was {old_total}).",
                        )

                    # persist freshest info
                    item["title"] = series.get("title") or item.get("title")
                    if new_total is not None:
                        item["total_chapters"] = new_total
                    item["last_checked"] = datetime.utcnow().isoformat() + "Z"
                    updated_any = True
                except Exception:
                    continue  # ignore single-series failures

            if updated_any:
                save_watchlist(wl)
        except Exception:
            # never die on background errors
            pass

        await asyncio.sleep(max(POLL_INTERVAL_SEC, 5))

# ---------- FastAPI app ----------
app = FastAPI(title="MangaNotify WebUI", version="0.1.0")

# CORS (handy for reverse proxies/admin UIs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static SPA
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return FileResponse("static/index.html")

# ---------- Core API ----------
@app.get("/api/health")
def health():
    return {"ok": True}

@app.get("/api/search")
async def search_endpoint(q: str = Query(..., min_length=1), page: int = 1, limit: int = 50):
    try:
        return await api_search(q, page=page, limit=limit)
    except httpx.HTTPStatusError as e:
        raise HTTPException(e.response.status_code, e.response.text or str(e))
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")

@app.get("/api/series/{series_id}")
async def series_endpoint(series_id: int):
    try:
        return await api_series_by_id(series_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Lookup failed: {e}")

@app.get("/api/watchlist")
def get_watchlist():
    return {"data": load_watchlist()}

@app.post("/api/watchlist")
async def add_watchlist(item: Dict[str, Any]):
    # expected: {"id": 377, "title": "...", "total_chapters": 1160}
    if "id" not in item:
        raise HTTPException(400, "Missing 'id'")
    wl = load_watchlist()
    sid = str(item["id"])
    if any(str(x.get("id")) == sid for x in wl):
        return {"ok": True, "message": "Already in watchlist"}
    # normalize total_chapters
    try:
        total = int(item.get("total_chapters")) if item.get("total_chapters") is not None else None
    except (TypeError, ValueError):
        total = None
    wl.append(
        {
            "id": item["id"],
            "title": item.get("title"),
            "total_chapters": total,
            "added_at": datetime.utcnow().isoformat() + "Z",
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

# ---------- Notifications router ----------
log = logging.getLogger("manganotify")
notify_router = APIRouter()

def _mask(s: Optional[str], keep: int = 4) -> str:
    if not s:
        return ""
    return s[:keep] + "…" if len(s) > keep else "…"

@notify_router.get("/api/notify/debug")
def notify_debug():
    token = PUSHOVER_APP_TOKEN
    user = PUSHOVER_USER_KEY
    return {
        "has_token": bool(token),
        "has_user": bool(user),
        "token_preview": _mask(token),
        "user_preview": _mask(user),
        "notes": "Both must be True for notifications to work.",
    }

@notify_router.post("/api/notify/test")
def notify_test():
    token = PUSHOVER_APP_TOKEN
    user = PUSHOVER_USER_KEY

    if not token or not user:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "message": "Missing Pushover env vars",
                "expected_env": ["PUSHOVER_APP_TOKEN", "PUSHOVER_USER_KEY"],
            },
        )

    payload = {
        "token": token,
        "user": user,
        "title": "MangaNotify",
        "message": "✅ MangaNotify test notification",
    }

    try:
        r = requests.post("https://api.pushover.net/1/messages.json", data=payload, timeout=12)
        try:
            js = r.json()
        except Exception:
            js = {"raw": r.text}

        success = (r.status_code == 200) and (js.get("status") == 1)

        if not success:
            log.error("Pushover send failed: http=%s body=%s", r.status_code, js)

        return JSONResponse(
            status_code=200 if success else 502,
            content={
                "ok": success,
                "http_status": r.status_code,
                "pushover_status": js.get("status"),
                "message": "Sent" if success else "Failed",
                "errors": js.get("errors"),
                "request_id": js.get("request"),
                "who": {"token": _mask(token), "user": _mask(user)},
            },
        )
    except requests.RequestException as e:
        log.exception("Network error calling Pushover")
        return JSONResponse(
            status_code=502,
            content={"ok": False, "message": "Network error to Pushover", "error": str(e)},
        )

# mount the router
app.include_router(notify_router)

# ---------- Lifecycle ----------
@app.on_event("startup")
async def on_startup():
    global poller_task
    if POLL_INTERVAL_SEC > 0:
        poller_task = asyncio.create_task(poll_watchlist_loop())

@app.on_event("shutdown")
async def on_shutdown():
    if poller_task:
        poller_task.cancel()
    await client.aclose()
