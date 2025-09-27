import asyncio, httpx
from fastapi import FastAPI
from .manga_api import api_series_by_id
from .watchlist import load_watchlist, save_watchlist, pick_cover, derive_last_chapter_at
from .notifications import add_notification, pushover
from ..core.config import settings
from ..core.utils import to_int, now_utc_iso

async def process_once(app: FastAPI):
    client: httpx.AsyncClient = app.state.client
    wl = load_watchlist()
    for it in wl:
        sid = it.get("id")
        if not sid: continue
        try:
            data   = await api_series_by_id(client, sid, full=True)
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
        except Exception:
            continue
    save_watchlist(wl)
    return {"checked": len(wl)}

async def poll_loop(app: FastAPI):
    interval = max(settings.POLL_INTERVAL_SEC, 0)
    while interval > 0:
        try:
            await process_once(app)
        except Exception:
            pass
        await asyncio.sleep(interval)
