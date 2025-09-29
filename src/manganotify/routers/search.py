import logging
from fastapi import APIRouter, HTTPException, Request, Query, Depends
from ..services.manga_api import api_search
from ..services.watchlist import normalize_series_min
from ..core.utils import to_bool_or_none, str_eq
from ..auth import require_auth

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/api/search")
async def search(
    request: Request,
    q: str = Query(..., min_length=1, max_length=100),
    page: int = Query(1, ge=1, le=1000),
    limit: int = Query(50, ge=1, le=100),
    status: str = Query(None, max_length=20, pattern=r"^[a-zA-Z0-9_-]*$"),
    type: str = Query(None, max_length=20, pattern=r"^[a-zA-Z0-9_-]*$"),
    content_rating: str = Query(None, max_length=20, pattern=r"^[a-zA-Z0-9_-]*$"),
    has_anime: str | bool | None = None,
    current_user: dict = Depends(require_auth)
):
    try:
        # Additional input sanitization
        q = q.strip()[:100]  # Ensure length limit
        if not q:
            raise HTTPException(400, "Search query cannot be empty")
        
        # Validate filter parameters
        if status and not status.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(400, "Invalid status filter")
        if type and not type.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(400, "Invalid type filter")
        if content_rating and not content_rating.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(400, "Invalid content rating filter")
        
        raw = await api_search(request.app.state.client, q, page=page, limit=limit)
        items = [normalize_series_min(it) for it in (raw.get("data") or raw.get("results") or [])]
        want_has_anime = to_bool_or_none(has_anime)

        def keep(it: dict) -> bool:
            if not str_eq(it.get("status"), status): return False
            if not str_eq(it.get("type"), type): return False
            if not str_eq(it.get("content_rating"), content_rating): return False
            if want_has_anime is not None:
                v = to_bool_or_none(it.get("has_anime"))
                if v is None or v is not want_has_anime: return False
            return True

        filtered = [it for it in items if keep(it)]
        out = dict(raw)
        out["data"] = filtered
        if isinstance(out.get("pagination"), dict):
            out["pagination"]["count"] = len(filtered)
        return out
    except Exception as e:
        logger.error("Search failed: %s", e)
        raise HTTPException(500, "Search failed")
