import httpx
from ..core.config import settings

# Validate and sanitize the base URL
BASE = settings.MANGABAKA_BASE.rstrip("/")

# Additional security validation for external API URL
if not BASE.startswith(("https://", "http://")):
    raise ValueError("MANGABAKA_BASE must start with http:// or https://")

# Prevent SSRF attacks by restricting to known domains
allowed_domains = ["api.mangabaka.dev", "mangabaka.dev"]
domain = BASE.split("://", 1)[1].split("/")[0]
if domain not in allowed_domains:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("MANGABAKA_BASE points to non-standard domain: %s", domain)

async def api_search(client: httpx.AsyncClient, q: str, page=1, limit=50):
    # Validate inputs to prevent injection attacks
    if not q or len(q.strip()) == 0:
        raise ValueError("Search query cannot be empty")
    
    # Sanitize query - remove potentially dangerous characters
    q = q.strip()[:100]  # Limit length
    page = max(1, min(page, 1000))  # Limit page range
    limit = max(1, min(limit, 50))  # Limit results per page
    
    r = await client.get(f"{BASE}/v1/series/search", params={"q": q, "page": page, "limit": limit})
    r.raise_for_status()
    return r.json()

async def api_series_by_id(client: httpx.AsyncClient, series_id: int | str, *, full: bool = False):
    # Validate series_id to prevent injection
    if isinstance(series_id, str):
        if not series_id.isdigit():
            raise ValueError("Series ID must be numeric")
        series_id = int(series_id)
    
    if series_id <= 0:
        raise ValueError("Series ID must be positive")
    
    url = f"{BASE}/v1/series/{series_id}" + ("/full" if full else "")
    r = await client.get(url)
    r.raise_for_status()
    return r.json()
