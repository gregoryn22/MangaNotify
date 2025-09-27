import httpx
from ..core.config import settings

BASE = settings.MANGABAKA_BASE.rstrip("/")

async def api_search(client: httpx.AsyncClient, q: str, page=1, limit=50):
    r = await client.get(f"{BASE}/v1/series/search", params={"q": q, "page": page, "limit": min(limit, 50)})
    r.raise_for_status()
    return r.json()

async def api_series_by_id(client: httpx.AsyncClient, series_id: int | str, *, full: bool = False):
    url = f"{BASE}/v1/series/{series_id}" + ("/full" if full else "")
    r = await client.get(url)
    r.raise_for_status()
    return r.json()
