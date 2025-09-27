from fastapi import APIRouter, HTTPException, Request, Query
from ..services.manga_api import api_search
from ..services.watchlist import normalize_series_min
from ..core.utils import to_bool_or_none, str_eq

router = APIRouter()

@router.get("/api/search")
async def search(
    request: Request,
    q: str = Query(..., min_length=1),
    page: int = 1, limit: int = 50,
    status: str | None = None, type: str | None = None,
    content_rating: str | None = None, has_anime: str | bool | None = None,
):
    try:
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
        raise HTTPException(500, f"Search failed: {e}")
