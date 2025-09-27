import httpx
from fastapi import Depends
from ..services.watchlist import load_watchlist, save_watchlist
from ..services.notifications import load_notifications, save_notifications

def get_client() -> httpx.AsyncClient:
    # provided via app.state in main; kept for typing
    raise RuntimeError("client is provided in app.lifespan")

# You can add other DI helpers here later (auth, stores, etc.)
