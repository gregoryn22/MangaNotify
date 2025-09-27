from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from ..services.notifications import load_notifications, save_notifications, add_notification, pushover
from ..core.config import settings

router = APIRouter()

@router.get("/api/health")
def health(): return {"ok": True}

@router.get("/api/notify/debug")
def notify_debug():
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
async def notify_test(request: Request):
    if not (settings.PUSHOVER_APP_TOKEN and settings.PUSHOVER_USER_KEY):
        return JSONResponse(status_code=500, content={"ok": False, "message": "Missing Pushover env vars"})
    res = await pushover(request.app.state.client, "MangaNotify", "✅ test")
    add_notification("test", {"title": "MangaNotify test", "message": "Manual test", "push_ok": bool(res.get("ok"))})
    return JSONResponse(status_code=200 if res.get("ok") else 502, content=res)

@router.get("/api/notifications")
def list_notifications(limit: int = 200):
    items = load_notifications()
    return {"data": items[: max(1, min(limit, 1000))]}

@router.delete("/api/notifications/{nid}")
def delete_notification(nid: int):
    items = load_notifications()
    before = len(items)
    items = [x for x in items if int(x.get("id", -1)) != int(nid)]
    save_notifications(items)
    return {"removed": before - len(items)}

@router.delete("/api/notifications")
def clear_notifications():
    save_notifications([]); return {"removed": "all"}
