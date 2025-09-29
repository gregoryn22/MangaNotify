from fastapi import APIRouter, HTTPException, Request, Query, Depends
from ..models.schemas import WatchlistAdd, ProgressPatch, StatusPatch, StatusLiteral, NotificationPreferencesPatch
from ..auth import require_auth
from ..services.watchlist import load_watchlist, save_watchlist, pick_cover, derive_last_chapter_at
from ..services.manga_api import api_series_by_id
from ..core.utils import to_int, now_utc_iso

router = APIRouter()

@router.get("/api/watchlist")
def get_watchlist(status: StatusLiteral | None = Query(default=None), current_user: dict = Depends(require_auth)):
    wl = load_watchlist()
    out = []
    for it in wl:
        total = to_int(it.get("total_chapters")) or 0
        last  = to_int(it.get("last_read")) or 0
        unread = max(total - last, 0)
        rec = {**it, "total_chapters": total or None, "last_read": last or 0,
               "unread": unread, "is_behind": unread>0}
        if status is None or rec.get("status") == status:
            out.append(rec)
    return {"data": out}

@router.post("/api/watchlist")
async def add_watch(item: WatchlistAdd, request: Request, current_user: dict = Depends(require_auth)):
    wl = load_watchlist()
    sid = str(item.id)
    if any(str(x.get("id")) == sid for x in wl):
        return {"ok": True, "message": "Already in watchlist"}
    # hydrate
    series = {}
    try:
        data = await api_series_by_id(request.app.state.client, sid, full=True)
        series = data.get("data") or data
        if str(series.get("state")) == "merged" and series.get("merged_with"):
            sid = str(series["merged_with"])
            data = await api_series_by_id(request.app.state.client, sid, full=True)
            series = data.get("data") or data
    except Exception:
        pass

    total = to_int(item.total_chapters) or to_int(series.get("total_chapters"))
    
    # Set up default notification preferences
    default_notifications = {
        "enabled": True,
        "pushover": True,
        "discord": True,
        "only_when_reading": True
    }
    
    # Use provided preferences or defaults
    notifications = default_notifications
    if item.notifications:
        notifications.update(item.notifications.dict())
    
    record = {
        "id": int(sid),
        "title": item.title or series.get("title"),
        "total_chapters": total,
        "last_read": to_int(item.last_read) or 0,
        "status": (item.status or "reading"),
        "cover": pick_cover(series) if series else None,
        "added_at": now_utc_iso(),
        "last_chapter_at": derive_last_chapter_at(series) if series else None,
        "last_checked": now_utc_iso(),
        "notifications": notifications,
    }
    wl.append(record); save_watchlist(wl)
    return {"ok": True}

@router.delete("/api/watchlist/{series_id}")
def remove(series_id: int, current_user: dict = Depends(require_auth)):
    wl = load_watchlist()
    before = len(wl)
    wl = [x for x in wl if str(x.get("id")) != str(series_id)]
    save_watchlist(wl)
    return {"removed": before - len(wl)}

@router.patch("/api/watchlist/{series_id}/progress")
def set_progress(series_id: int, body: ProgressPatch, current_user: dict = Depends(require_auth)):
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            total = to_int(it.get("total_chapters"))
            last  = to_int(it.get("last_read")) or 0
            if body.mark_latest:
                it["last_read"] = total if total is not None else last
            elif body.decrement is not None:
                it["last_read"] = max(0, last - (to_int(body.decrement) or 1))
            elif body.last_read is not None:
                lr = to_int(body.last_read)
                if lr is None: raise HTTPException(400, "last_read must be an integer")
                it["last_read"] = max(0, lr)
            else:
                raise HTTPException(400, "No recognized progress action")
            it["last_checked"] = now_utc_iso()
            save_watchlist(wl)
            return {"ok": True, "last_read": it["last_read"]}
    raise HTTPException(404, "Not in watchlist")

@router.post("/api/watchlist/{series_id}/read/next")
def read_next(series_id: int, current_user: dict = Depends(require_auth)):
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            it["last_read"] = (to_int(it.get("last_read")) or 0) + 1
            it["last_checked"] = now_utc_iso()
            save_watchlist(wl)
            return {"ok": True, "last_read": it["last_read"]}
    raise HTTPException(404, "Not in watchlist")


@router.patch("/api/watchlist/{series_id}/status")
def set_status(series_id: int, body: StatusPatch, current_user: dict = Depends(require_auth)):
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            it["status"] = body.status
            it["last_checked"] = now_utc_iso()
            save_watchlist(wl)
            return {"ok": True, "status": it["status"]}
    raise HTTPException(404, "Not in watchlist")


@router.patch("/api/watchlist/{series_id}/notifications")
def update_notification_preferences(series_id: int, body: NotificationPreferencesPatch, current_user: dict = Depends(require_auth)):
    """Update notification preferences for a specific series."""
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            # Initialize notifications object if it doesn't exist
            if "notifications" not in it:
                it["notifications"] = {}
            
            # Update only the provided fields
            if body.enabled is not None:
                it["notifications"]["enabled"] = body.enabled
            if body.pushover is not None:
                it["notifications"]["pushover"] = body.pushover
            if body.discord is not None:
                it["notifications"]["discord"] = body.discord
            if body.only_when_reading is not None:
                it["notifications"]["only_when_reading"] = body.only_when_reading
            
            it["last_checked"] = now_utc_iso()
            save_watchlist(wl)
            return {"ok": True, "notifications": it["notifications"]}
    raise HTTPException(404, "Not in watchlist")


@router.get("/api/watchlist/{series_id}/notifications")
def get_notification_preferences(series_id: int, current_user: dict = Depends(require_auth)):
    """Get notification preferences for a specific series."""
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            # Return default preferences if not set
            notif_prefs = it.get("notifications", {
                "enabled": True,
                "pushover": True,
                "discord": True,
                "only_when_reading": True
            })
            return {"ok": True, "notifications": notif_prefs}
    raise HTTPException(404, "Not in watchlist")
