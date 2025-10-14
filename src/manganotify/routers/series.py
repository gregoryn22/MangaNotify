import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request

from ..auth import require_auth
from ..services.manga_api import api_series_by_id
from ..services.watchlist import derive_last_chapter_at, normalize_series_min

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/series/{series_id}")
async def series(
    request: Request,
    series_id: int = Path(..., ge=1, le=999999999),
    full: bool = Query(True),
    current_user: dict = Depends(require_auth),
):
    try:
        # Additional validation
        if series_id <= 0:
            raise HTTPException(400, "Invalid series ID")

        data = await api_series_by_id(
            request.app.state.client, series_id, full=bool(full)
        )
        series = data.get("data") or data
        minimal = normalize_series_min(series)
        minimal["last_chapter_at"] = derive_last_chapter_at(series)
        merged = (
            series.get("merged_with") if str(series.get("state")) == "merged" else None
        )
        return {
            "status": 200,
            "data": series,
            "minimal": minimal,
            "merged_with": merged,
        }
    except Exception as e:
        logger.error("Series lookup failed: %s", e)
        raise HTTPException(500, "Lookup failed") from e
