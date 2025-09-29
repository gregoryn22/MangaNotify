from typing import Dict, Any, List, Optional
import httpx
from ..core.config import NOTIFY_PATH, settings
from ..storage.json_store import load_json, save_json
from ..core.utils import now_utc_iso

def load_notifications() -> List[Dict[str, Any]]:
    return load_json(NOTIFY_PATH, [])

def save_notifications(items: List[Dict[str, Any]]):
    save_json(NOTIFY_PATH, items, compact=True)

def next_notification_id(items: List[Dict[str, Any]]) -> int:
    try: return max((int(x.get("id", 0)) for x in items), default=0) + 1
    except Exception: return 1

def add_notification(kind: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    items = load_notifications()
    rec = {"id": next_notification_id(items), "kind": kind, "detected_at": now_utc_iso(), **payload}
    items.insert(0, rec)
    save_notifications(items)
    return rec

async def pushover(client: httpx.AsyncClient, title: str, message: str) -> Dict[str, Any]:
    # Get decrypted credentials
    app_token = settings.get_decrypted_pushover_app_token()
    user_key = settings.get_decrypted_pushover_user_key()
    
    if not (app_token and user_key):
        return {"ok": False, "reason": "Missing PUSHOVER_* envs"}
    
    r = await client.post(
        "https://api.pushover.net/1/messages.json",
        data={"token": app_token, "user": user_key,
              "title": title, "message": message},
        timeout=15.0,
    )
    js = {}
    try: js = r.json()
    except Exception: pass
    return {"ok": r.status_code == 200 and js.get("status") == 1, "status": r.status_code, "raw": js}

async def discord_notify(client: httpx.AsyncClient, title: str, message: str) -> Dict[str, Any]:
    # Get decrypted webhook URL
    webhook_url = settings.get_decrypted_discord_webhook_url()
    
    if not (settings.DISCORD_ENABLED and webhook_url):
        return {"ok": False, "reason": "Discord notifications not enabled or webhook missing"}
    
    payload = {
        "embeds": [{
            "title": title,
            "description": message,
            "color": 0x5865F2  # Discord blurple
        }]
    }
    try:
        r = await client.post(
            webhook_url,
            json=payload,
            timeout=15.0,
        )
        return {"ok": r.status_code in (200, 204), "status": r.status_code, "raw": await r.aread()}
    except Exception as e:
        return {"ok": False, "reason": str(e)}
