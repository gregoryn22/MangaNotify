import mimetypes, contextlib, asyncio, httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from pathlib import Path

from .core.config import settings
from .services.poller import poll_loop, process_once
from .routers import search, series, watchlist, notify

# ensure correct MIME
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

ASSETS_DIR = Path(__file__).resolve().parent / "static"   # <- sibling 'static'


def create_app() -> FastAPI:
    app = FastAPI(title="MangaNotify", version="0.4")

    @app.on_event("startup")
    async def startup():
        app.state.client = httpx.AsyncClient(timeout=20.0)
        app.state.poller_task = None
        if settings.POLL_INTERVAL_SEC > 0:
            app.state.poller_task = asyncio.create_task(poll_loop(app))

    @app.on_event("shutdown")
    async def shutdown():
        if app.state.poller_task:
            app.state.poller_task.cancel()
            with contextlib.suppress(Exception):
                await app.state.poller_task
        await app.state.client.aclose()

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # static + index
    app.mount("/static", StaticFiles(directory=str(ASSETS_DIR)), name="static")
    app.mount("/images", StaticFiles(directory=str(ASSETS_DIR / "images")), name="images")

    @app.get("/")
    async def index():
        return FileResponse(str(ASSETS_DIR / "index.html"))

    # routers
    app.include_router(search.router)
    app.include_router(series.router)
    app.include_router(watchlist.router)
    app.include_router(notify.router)

    # optional: expose /api/watchlist/refresh using the shared processor
    @app.post("/api/watchlist/refresh")
    async def trigger_refresh():
        return await process_once(app)

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn, os, pathlib

    # Ensure cwd is repo root (so .env and data/ resolve consistently)
    os.chdir(pathlib.Path(__file__).resolve().parents[2])

    uvicorn.run(
        "manganotify.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8999")),
        reload=False,
        app_dir="src",  # <- important when running from repo root
    )

