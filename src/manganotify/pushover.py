# deps: requests, keyring (optional but recommended)
import os, requests

def send_pushover(message: str, *, title="MangaBaka", priority=0,
                  user_key: str | None = None, app_token: str | None = None) -> None:
    user_key  = user_key  or os.getenv("PUSHOVER_USER_KEY")
    app_token = app_token or os.getenv("PUSHOVER_APP_TOKEN")
    if not user_key or not app_token:
        return  # silently skip if not configured

    r = requests.post("https://api.pushover.net/1/messages.json", timeout=15, data={
        "token": app_token,
        "user": user_key,
        "message": message,
        "title": title,
        "priority": str(priority),
    })
    r.raise_for_status()
