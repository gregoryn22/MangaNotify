import logging
import httpx
from fastapi import APIRouter, HTTPException, Request, Query, Path, Depends
from ..services.manga_api import api_series_by_id
from ..services.watchlist import normalize_series_min, derive_last_chapter_at
from ..auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/series/{series_id}")
async def series(request: Request, series_id: int = Path(..., ge=1, le=999999999), full: bool = Query(True), current_user: dict = Depends(require_auth)):
    try:
        if series_id <= 0:
            raise HTTPException(400, "Invalid series ID")

        data = await api_series_by_id(request.app.state.client, series_id, full=bool(full))
        series = data.get("data") or data
        minimal = normalize_series_min(series)
        minimal["last_chapter_at"] = derive_last_chapter_at(series)
        merged = series.get("merged_with") if str(series.get("state")) == "merged" else None
        return {"status": 200, "data": series, "minimal": minimal, "merged_with": merged}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 404:
            raise HTTPException(404, "Series not found") from exc
        detail = exc.response.text or "Upstream service error"
        logger.warning("Series lookup failed with upstream status %s: %s", status_code, detail)
        raise HTTPException(status_code, detail) from exc
    except httpx.RequestError as exc:
        logger.error("Series lookup request failed: %s", exc, exc_info=True)
        raise HTTPException(502, "Upstream service unavailable") from exc
    except Exception as exc:
        logger.error("Series lookup failed: %s", exc, exc_info=True)
        raise HTTPException(500, "Lookup failed") from exc
