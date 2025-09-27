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
    if not (settings.PUSHOVER_APP_TOKEN and settings.PUSHOVER_USER_KEY):
        return {"ok": False, "reason": "Missing PUSHOVER_* envs"}
    r = await client.post(
        "https://api.pushover.net/1/messages.json",
        data={"token": settings.PUSHOVER_APP_TOKEN, "user": settings.PUSHOVER_USER_KEY,
              "title": title, "message": message},
        timeout=15.0,
    )
    js = {}
    try: js = r.json()
    except Exception: pass
    return {"ok": r.status_code == 200 and js.get("status") == 1, "status": r.status_code, "raw": js}
