# src/manganotify/routers/health.py
"""Health check endpoints for monitoring and status."""

from fastapi import APIRouter, Depends, Request

from ..auth import require_auth

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    """Basic health check endpoint - returns 200 OK if service is running."""
    return {"ok": True}


@router.get("/health/details")
async def health_details(request: Request, current_user: dict = Depends(require_auth)):
    """
    Detailed health information including poller statistics.
    Requires authentication.
    """
    app = request.app
    settings = getattr(app.state, "settings", None)
    stats = getattr(app.state, "poll_stats", None) or {}

    poll_interval = settings.POLL_INTERVAL_SEC if settings else 0

    return {"ok": True, "poll": stats, "interval_sec": poll_interval}
