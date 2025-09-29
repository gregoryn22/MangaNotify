from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ..services.notifications import load_notifications, save_notifications, add_notification, pushover, discord_notify
from ..auth import require_auth

router = APIRouter()

@router.get("/api/health")
def health(): return {"ok": True}

@router.get("/api/notify/debug")
def notify_debug(request: Request, current_user: dict = Depends(require_auth)):
    """Debug endpoint - requires authentication to prevent information disclosure."""
    # Get settings from app state
    settings = request.app.state.settings
    
    def mask(s: str | None, keep=4):
        if not s: return ""
        return (s[:keep] + "…") if len(s) > keep else "…"
    return {
        "has_token": bool(settings.PUSHOVER_APP_TOKEN),
        "has_user": bool(settings.PUSHOVER_USER_KEY),
        "token_preview": mask(settings.PUSHOVER_APP_TOKEN),
        "user_preview": mask(settings.PUSHOVER_USER_KEY),
    }

@router.post("/api/notify/test")
async def notify_test(request: Request, current_user: dict = Depends(require_auth)):
    # Get settings from app state
    settings = request.app.state.settings
    
    if not (settings.PUSHOVER_APP_TOKEN and settings.PUSHOVER_USER_KEY):
        return JSONResponse(status_code=500, content={"ok": False, "message": "Missing Pushover env vars"})
    res = await pushover(request.app.state.client, "MangaNotify", "✅ test")
    add_notification("test", {"title": "MangaNotify test", "message": "Manual test", "push_ok": bool(res.get("ok"))})
    return JSONResponse(status_code=200 if res.get("ok") else 502, content=res)

@router.get("/api/notifications")
def list_notifications(limit: int = 200, current_user: dict = Depends(require_auth)):
    items = load_notifications()
    return {"data": items[: max(1, min(limit, 1000))]}

@router.delete("/api/notifications/{nid}")
def delete_notification(nid: int, current_user: dict = Depends(require_auth)):
    items = load_notifications()
    before = len(items)
    items = [x for x in items if int(x.get("id", -1)) != int(nid)]
    save_notifications(items)
    return {"removed": before - len(items)}

@router.delete("/api/notifications")
def clear_notifications(current_user: dict = Depends(require_auth)):
    save_notifications([]); return {"removed": "all"}

class DiscordSettings(BaseModel):
    webhook_url: str = ""
    enabled: bool = False

@router.get("/api/discord/settings")
async def get_discord_settings(request: Request, current_user: dict = Depends(require_auth)):
    # Get settings from app state
    settings = request.app.state.settings
    
    return {
        "webhook_url": settings.DISCORD_WEBHOOK_URL or "",
        "enabled": bool(settings.DISCORD_ENABLED),
    }

@router.post("/api/discord/settings")
async def set_discord_settings(body: DiscordSettings, request: Request, current_user: dict = Depends(require_auth)):
    # Get settings from app state
    settings = request.app.state.settings
    
    # Save to settings (and persist if needed)
    settings.DISCORD_WEBHOOK_URL = body.webhook_url
    settings.DISCORD_ENABLED = body.enabled
    # Optionally: persist to disk or .env here
    return {"ok": True}

@router.post("/api/discord/test")
async def discord_test(request: Request, current_user: dict = Depends(require_auth)):
    client = request.app.state.client
    result = await discord_notify(client, "MangaNotify Test", "This is a test notification from MangaNotify.")
    return JSONResponse(result)
