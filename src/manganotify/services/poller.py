import asyncio, random, httpx, logging
from fastapi import FastAPI
from .manga_api import api_series_by_id
from .watchlist import load_watchlist, save_watchlist, pick_cover, derive_last_chapter_at
from .notifications import add_notification, pushover
from ..core.config import settings
from ..core.utils import to_int, now_utc_iso

async def process_once(app: FastAPI):
    """One pass over the watchlist; resilient per-item handling."""
    client: httpx.AsyncClient = app.state.client
    wl = load_watchlist()
    for it in wl:
        sid = it.get("id")
        if not sid: continue
        try:
            # basic retry for transient upstream issues
            attempts = 0
            last_exc = None
            while attempts < 3:
                try:
                    data = await api_series_by_id(client, sid, full=True)
                    break
                except Exception as e:
                    last_exc = e
                    attempts += 1
                    await asyncio.sleep(0.5 * attempts)
            if attempts >= 3 and last_exc is not None:
                logging.warning("poller: failed to fetch series %s after retries: %s", sid, last_exc)
                continue
            # normal path after successful fetch
            series = data.get("data") or data

            if str(series.get("state")) == "merged" and series.get("merged_with"):
                it["id"] = series["merged_with"]
                data   = await api_series_by_id(client, it["id"], full=True)
                series = data.get("data") or data

            new_total = to_int(series.get("total_chapters"))
            old_total = to_int(it.get("total_chapters"))
            last_read = to_int(it.get("last_read")) or 0

            if new_total is not None and old_total is not None and new_total > old_total:
                unread = max(new_total - last_read, 0)
                msg = f"{it.get('title','(unknown)')} now has {new_total} chapters."
                if unread > 0: msg += f" You’re {unread} behind."
                res = await pushover(client, "New chapter(s)", msg)
                add_notification("chapter_update",
                                 {"series_id": it.get("id"), "title": it.get("title"),
                                  "old_total": old_total, "new_total": new_total,
                                  "unread": unread, "message": msg, "push_ok": bool(res.get('ok'))})

            it["title"] = series.get("title") or it.get("title")
            if new_total is not None: it["total_chapters"] = new_total
            if (c := pick_cover(series)): it["cover"] = c
            it["last_chapter_at"] = derive_last_chapter_at(series)
            it["last_checked"] = now_utc_iso()
        except Exception as e:
            logging.exception("poller: error processing series %s: %s", sid, e)
            continue
    save_watchlist(wl)
    return {"checked": len(wl)}

async def poll_loop(app: FastAPI):
    """Background loop with jitter and error isolation."""
    base_interval = max(settings.POLL_INTERVAL_SEC, 0)
    # track some basic stats for /api/health/details
    app.state.poll_stats = {"last_ok": None, "last_error": None}
    while base_interval > 0:
        try:
            await process_once(app)
            app.state.poll_stats["last_ok"] = now_utc_iso()
        except Exception as e:
            app.state.poll_stats["last_error"] = {"at": now_utc_iso(), "error": str(e)}
            logging.exception("poller: iteration failed: %s", e)
        # add small jitter to avoid synchronized hits
        jitter = random.uniform(-0.1, 0.1) * base_interval
        sleep_for = max(1.0, base_interval + jitter)
        try:
            await asyncio.sleep(sleep_for)
        except asyncio.CancelledError:
            # graceful shutdown
            break
