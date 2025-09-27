from fastapi import APIRouter, HTTPException, Request
from ..services.watchlist import load_watchlist, save_watchlist, pick_cover, derive_last_chapter_at
from ..services.manga_api import api_series_by_id
from ..core.utils import to_int, now_utc_iso

router = APIRouter()

@router.get("/api/watchlist")
def get_watchlist():
    wl = load_watchlist()
    out = []
    for it in wl:
        total = to_int(it.get("total_chapters")) or 0
        last  = to_int(it.get("last_read")) or 0
        unread = max(total - last, 0)
        out.append({**it, "total_chapters": total or None, "last_read": last or 0,
                    "unread": unread, "is_behind": unread>0})
    return {"data": out}

@router.post("/api/watchlist")
async def add_watch(item: dict, request: Request):
    if "id" not in item: raise HTTPException(400, "Missing 'id'")
    wl = load_watchlist()
    sid = str(item["id"])
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

    total = to_int(item.get("total_chapters")) or to_int(series.get("total_chapters"))
    record = {
        "id": int(sid),
        "title": item.get("title") or series.get("title"),
        "total_chapters": total,
        "last_read": to_int(item.get("last_read")) or 0,
        "cover": pick_cover(series) if series else None,
        "added_at": now_utc_iso(),
        "last_chapter_at": derive_last_chapter_at(series) if series else None,
        "last_checked": now_utc_iso(),
    }
    wl.append(record); save_watchlist(wl)
    return {"ok": True}

@router.delete("/api/watchlist/{series_id}")
def remove(series_id: int):
    wl = load_watchlist()
    before = len(wl)
    wl = [x for x in wl if str(x.get("id")) != str(series_id)]
    save_watchlist(wl)
    return {"removed": before - len(wl)}

@router.patch("/api/watchlist/{series_id}/progress")
def set_progress(series_id: int, body: dict):
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            total = to_int(it.get("total_chapters"))
            last  = to_int(it.get("last_read")) or 0
            if body.get("mark_latest"):
                it["last_read"] = total if total is not None else last
            elif "decrement" in body:
                it["last_read"] = max(0, last - (to_int(body.get("decrement")) or 1))
            elif "last_read" in body:
                lr = to_int(body.get("last_read"))
                if lr is None: raise HTTPException(400, "last_read must be an integer")
                it["last_read"] = max(0, lr)
            else:
                raise HTTPException(400, "No recognized progress action")
            it["last_checked"] = now_utc_iso()
            save_watchlist(wl)
            return {"ok": True, "last_read": it["last_read"]}
    raise HTTPException(404, "Not in watchlist")

@router.post("/api/watchlist/{series_id}/read/next")
def read_next(series_id: int):
    wl = load_watchlist()
    for it in wl:
        if str(it.get("id")) == str(series_id):
            it["last_read"] = (to_int(it.get("last_read")) or 0) + 1
            it["last_checked"] = now_utc_iso()
            save_watchlist(wl)
            return {"ok": True, "last_read": it["last_read"]}
    raise HTTPException(404, "Not in watchlist")
