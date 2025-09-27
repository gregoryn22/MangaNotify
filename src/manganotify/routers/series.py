from fastapi import APIRouter, HTTPException, Request
from ..services.manga_api import api_series_by_id
from ..services.watchlist import normalize_series_min, derive_last_chapter_at

router = APIRouter()

@router.get("/api/series/{series_id}")
async def series(request: Request, series_id: int, full: bool = True):
    try:
        data = await api_series_by_id(request.app.state.client, series_id, full=bool(full))
        series = data.get("data") or data
        minimal = normalize_series_min(series)
        minimal["last_chapter_at"] = derive_last_chapter_at(series)
        merged = series.get("merged_with") if str(series.get("state")) == "merged" else None
        return {"status": 200, "data": series, "minimal": minimal, "merged_with": merged}
    except Exception as e:
        raise HTTPException(500, f"Lookup failed: {e}")
