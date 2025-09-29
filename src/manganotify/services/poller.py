import asyncio, random, httpx, logging
from fastapi import FastAPI
from .manga_api import api_series_by_id
from .watchlist import load_watchlist, save_watchlist, pick_cover, derive_last_chapter_at
from .notifications import add_notification, pushover
from ..core.config import settings
from ..core.utils import to_int, now_utc_iso


def _should_send_notification(series_item: dict) -> bool:
    """Determine if notifications should be sent for this series based on preferences."""
    notif_prefs = series_item.get("notifications", {})
    
    # Check if notifications are enabled for this series
    if not notif_prefs.get("enabled", True):
        return False
    
    # Check if we should only notify when status is 'reading'
    if notif_prefs.get("only_when_reading", True):
        series_status = series_item.get("status", "reading")
        if series_status not in ["reading", "releasing"]:  # Allow both reading and releasing statuses
            return False
    
    return True

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
                if unread > 0: msg += f" You're {unread} behind."
                
                # Check notification preferences for this series
                should_notify = _should_send_notification(it)
                
                if should_notify:
                    # Send notifications based on preferences
                    pushover_result = None
                    discord_result = None
                    
                    # Get notification preferences (default to enabled if not set)
                    notif_prefs = it.get("notifications", {})
                    pushover_enabled = notif_prefs.get("pushover", True)
                    discord_enabled = notif_prefs.get("discord", True)
                    
                    if pushover_enabled:
                        pushover_result = await pushover(client, "New chapter(s)", msg)
                    
                    if discord_enabled:
                        from .notifications import discord_notify
                        discord_result = await discord_notify(client, "New chapter(s)", msg)
                    
                    # Log notification results
                    push_ok = bool(pushover_result and pushover_result.get('ok')) if pushover_result else False
                    discord_ok = bool(discord_result and discord_result.get('ok')) if discord_result else False
                    
                    add_notification("chapter_update",
                                     {"series_id": it.get("id"), "title": it.get("title"),
                                      "old_total": old_total, "new_total": new_total,
                                      "unread": unread, "message": msg, 
                                      "push_ok": push_ok, "discord_ok": discord_ok,
                                      "notifications_enabled": True})
                else:
                    # Still log the update but don't send notifications
                    add_notification("chapter_update",
                                     {"series_id": it.get("id"), "title": it.get("title"),
                                      "old_total": old_total, "new_total": new_total,
                                      "unread": unread, "message": msg,
                                      "push_ok": False, "discord_ok": False,
                                      "notifications_enabled": False})

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
    base_interval = settings.POLL_INTERVAL_SEC
    # track some basic stats for /api/health/details
    app.state.poll_stats = {"last_ok": None, "last_error": None}
    
    # Early exit if polling is disabled
    if base_interval <= 0:
        logging.info("Poller disabled (POLL_INTERVAL_SEC=%d)", base_interval)
        return
    
    logging.info("Starting poller with interval %d seconds", base_interval)
    
    while True:  # Changed to True, but we'll break on cancellation
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
            logging.info("Poller cancelled, shutting down")
            break
