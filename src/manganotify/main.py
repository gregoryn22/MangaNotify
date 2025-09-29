# src/manganotify/main.py
from __future__ import annotations

import mimetypes
import contextlib
from contextlib import asynccontextmanager
import asyncio
from pathlib import Path

import httpx
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
import uuid


from .core.config import create_settings
from .core.utils import setup_logging
from .services.poller import poll_loop, process_once
from .routers import search, series, watchlist, notify, auth, setup
from .auth import require_auth


# MIME fixes (Windows sometimes misses these)
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

ASSETS_DIR = Path(__file__).resolve().parent / "static"   # /src/manganotify/static


def create_app() -> FastAPI:
    settings = create_settings()
    setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
    logger = logging.getLogger(__name__)
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.client = httpx.AsyncClient(timeout=20.0)
        app.state.settings = settings  # Store settings in app state
        app.state.poller_task = None
        
        # Only start poller if interval is positive
        if settings.POLL_INTERVAL_SEC > 0:
            logger.info("Starting background poller with interval %d seconds", settings.POLL_INTERVAL_SEC)
            app.state.poller_task = asyncio.create_task(poll_loop(app))
        else:
            logger.info("Background poller disabled (POLL_INTERVAL_SEC=%d)", settings.POLL_INTERVAL_SEC)
        
        try:
            yield
        finally:
            poller_task = getattr(app.state, "poller_task", None)
            if poller_task:
                logger.info("Shutting down background poller")
                poller_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await poller_task
            client = getattr(app.state, "client", None)
            if client:
                await client.aclose()

    
    # Security validation on startup
    if settings.AUTH_ENABLED:
        if not settings.AUTH_SECRET_KEY:
            raise RuntimeError("AUTH_ENABLED=true but AUTH_SECRET_KEY is not set")
        if len(settings.AUTH_SECRET_KEY) < 32:
            raise RuntimeError("AUTH_SECRET_KEY must be at least 32 characters long")
        if not settings.AUTH_PASSWORD:
            raise RuntimeError("AUTH_ENABLED=true but AUTH_PASSWORD is not set")
        
        # Validate password is hashed
        if not settings.AUTH_PASSWORD.startswith("$2b$"):
            logger.warning("AUTH_PASSWORD appears to be plain text - this is insecure!")
        
        # Validate username format
        if not settings.AUTH_USERNAME.replace("_", "").replace("-", "").isalnum():
            raise RuntimeError("AUTH_USERNAME contains invalid characters")
        
        logger.info("Authentication enabled with secure configuration")
    else:
        logger.warning("Authentication is DISABLED - application is open to all users")
    
    # Validate CORS configuration
    if settings.CORS_ALLOW_ORIGINS == "*":
        logger.warning("CORS_ALLOW_ORIGINS is set to '*' - this allows any origin!")
    
    # Validate external API URL
    if not settings.MANGABAKA_BASE.startswith(("https://", "http://")):
        raise RuntimeError("MANGABAKA_BASE must start with http:// or https://")
    
    # Validate port number
    if settings.PORT < 1 or settings.PORT > 65535:
        raise RuntimeError("PORT must be between 1 and 65535")
    
    # Validate poll interval
    if settings.POLL_INTERVAL_SEC < 0:
        raise RuntimeError("POLL_INTERVAL_SEC must be non-negative")
    
    # Validate token expiration
    if settings.AUTH_TOKEN_EXPIRE_HOURS < 1 or settings.AUTH_TOKEN_EXPIRE_HOURS > 8760:  # Max 1 year
        raise RuntimeError("AUTH_TOKEN_EXPIRE_HOURS must be between 1 and 8760")
    
    # Validate log level
    valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
    if settings.LOG_LEVEL not in valid_log_levels:
        raise RuntimeError(f"LOG_LEVEL must be one of {valid_log_levels}")
    
    # Validate log format
    valid_log_formats = ["plain", "json"]
    if settings.LOG_FORMAT not in valid_log_formats:
        raise RuntimeError(f"LOG_FORMAT must be one of {valid_log_formats}")
    
    app = FastAPI(
        title="MangaNotify", 
        version="0.4", 
        lifespan=lifespan,
        # Security: Limit request size to prevent DoS attacks
        docs_url=None,  # Disable docs in production
        redoc_url=None,  # Disable redoc in production
        openapi_url=None if settings.LOG_LEVEL != "DEBUG" else "/openapi.json"  # Hide API schema in production
    )

    # --- middleware ---
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Request size limiting middleware
    @app.middleware("http")
    async def limit_request_size(request, call_next):
        # Limit request body size to prevent DoS attacks
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request body too large"
            )
        response = await call_next(request)
        return response
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # CSRF Protection middleware
    @app.middleware("http")
    async def csrf_protection(request, call_next):
        # Skip CSRF for GET, HEAD, OPTIONS requests
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            response = await call_next(request)
        else:
            # For state-changing requests, check Origin header
            origin = request.headers.get("origin")
            referer = request.headers.get("referer")
            
            # Allow requests from same origin or configured CORS origins
            if origin:
                allowed_origins = settings.cors_allow_origins_list
                if "*" not in allowed_origins and origin not in allowed_origins:
                    logger.warning("CSRF protection: Invalid origin %s", origin)
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Invalid origin"
                    )
            
            response = await call_next(request)
        
        return response

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        
        # Content Security Policy - strict for production
        # Extract domain from MANGABAKA_BASE for image sources
        mangabaka_domain = settings.MANGABAKA_BASE.split("://", 1)[1].split("/")[0]
        
        # Common image hosting domains that manga APIs might use
        image_domains = [
            mangabaka_domain,
            "mangabaka.dev",  # Main domain
            "cdn.mangabaka.dev",  # CDN domain
            "images.mangabaka.dev",  # Images subdomain
            "static.mangabaka.dev",  # Static subdomain
        ]
        
        # Create img-src and connect-src directives (allow both HTTP and HTTPS)
        img_sources = "'self' data: " + " ".join(f"https://{domain} http://{domain}" for domain in image_domains)
        connect_sources = "'self' " + " ".join(f"https://{domain} http://{domain}" for domain in image_domains)
        
        if settings.CORS_ALLOW_ORIGINS == "*":
            # Development mode - more permissive CSP
            csp = f"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src {img_sources}; connect-src {connect_sources}"
        else:
            # Production mode - strict CSP but allow manga cover images
            csp = f"default-src 'self'; script-src 'self'; style-src 'self'; img-src {img_sources}; connect-src {connect_sources}"
        response.headers["Content-Security-Policy"] = csp
        
        # Log CSP for debugging (only in debug mode)
        if settings.LOG_LEVEL == "DEBUG":
            logger.debug(f"CSP applied: {csp}")
        
        # HSTS (if HTTPS)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response
    
    # Rate limiting middleware
    @app.middleware("http")
    async def rate_limit(request, call_next):
        import time
        from collections import defaultdict
        
        # Get client IP (consider X-Forwarded-For for reverse proxy)
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Initialize rate limiting storage (in production, use Redis)
        if not hasattr(app.state, "rate_limits"):
            app.state.rate_limits = defaultdict(list)
        
        current_time = time.time()
        rate_limits = app.state.rate_limits
        
        # Clean old entries (older than 1 minute)
        rate_limits[client_ip] = [t for t in rate_limits[client_ip] if current_time - t < 60]
        
        # Rate limit login attempts more strictly
        if request.url.path == "/api/auth/login":
            # Allow 10 login attempts per minute per IP (more reasonable for testing)
            if len(rate_limits[client_ip]) >= 10:
                logger.warning("Rate limit exceeded for login attempts from IP: %s", client_ip)
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Please try again later."
                )
            rate_limits[client_ip].append(current_time)
        
        # Rate limit search endpoint more strictly (potential DoS target)
        elif request.url.path == "/api/search":
            if len(rate_limits[client_ip]) >= 20:  # 20 searches per minute
                logger.warning("Rate limit exceeded for search requests from IP: %s", client_ip)
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many search requests. Please slow down."
                )
            rate_limits[client_ip].append(current_time)
        
        # Rate limit setup endpoints more strictly (potential abuse target)
        elif request.url.path.startswith("/api/setup/"):
            if len(rate_limits[client_ip]) >= 10:  # 10 setup requests per minute
                logger.warning("Rate limit exceeded for setup requests from IP: %s", client_ip)
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many setup requests. Please slow down."
                )
            rate_limits[client_ip].append(current_time)
        
        # General rate limiting (100 requests per minute per IP)
        elif request.url.path.startswith("/api/"):
            if len(rate_limits[client_ip]) >= 100:
                logger.warning("Rate limit exceeded for API requests from IP: %s", client_ip)
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please slow down."
                )
            rate_limits[client_ip].append(current_time)
        
        response = await call_next(request)
        return response

    # request logging + correlation IDs
    @app.middleware("http")
    async def log_requests(request, call_next):
        start = time.perf_counter()
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        response = None
        try:
            response = await call_next(request)
        except Exception:
            # ensure request id even on exception
            logging.exception("unhandled error while processing %s %s [rid=%s]",
                              request.method, request.url.path, request_id)
            raise
        finally:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            # Only log path (no query) to avoid leaking info
            logging.info("%s %s -> %s in %dms [rid=%s]",
                         request.method, request.url.path,
                         getattr(response, "status_code", "-"),
                         elapsed_ms, request_id)
        # surface request id to clients
        try:
            response.headers["X-Request-ID"] = request_id
        except Exception:
            pass
        return response

    # --- static + index ---
    # Secure static file serving with path validation
    class SecureStaticFiles(StaticFiles):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
        
        async def get_response(self, path: str, scope):
            # Prevent path traversal attacks
            if ".." in path or path.startswith("/"):
                from fastapi import HTTPException, status
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Path traversal not allowed")
            
            response = await super().get_response(path, scope)
            
            # Add security headers to static files
            if hasattr(response, 'headers'):
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["Cache-Control"] = "public, max-age=31536000"  # 1 year cache for static assets
            
            return response
    
    app.mount("/static", SecureStaticFiles(directory=str(ASSETS_DIR)), name="static")
    app.mount("/images", SecureStaticFiles(directory=str(ASSETS_DIR / "images")), name="images")

    @app.get("/")
    async def index():
        return FileResponse(str(ASSETS_DIR / "index.html"))
    
    @app.get("/setup")
    async def setup_page():
        return FileResponse(str(ASSETS_DIR / "setup.html"))

    # --- routers ---
    app.include_router(setup.router)  # Setup wizard (no auth required)
    app.include_router(auth.router)
    app.include_router(search.router)
    app.include_router(series.router)
    app.include_router(watchlist.router)
    app.include_router(notify.router)

    # utility endpoint
    @app.post("/api/watchlist/refresh")
    async def trigger_refresh(current_user: dict = Depends(require_auth)):
        return await process_once(app)

    # health details
    @app.get("/api/health/details")
    async def health_details(current_user: dict = Depends(require_auth)):
        stats = getattr(app.state, "poll_stats", None) or {}
        return {"ok": True, "poll": stats, "interval_sec": settings.POLL_INTERVAL_SEC}

    # Debug endpoint for CSP and image testing
    @app.get("/api/debug/csp")
    async def debug_csp():
        """Debug endpoint to inspect CSP settings."""
        mangabaka_domain = settings.MANGABAKA_BASE.split("://", 1)[1].split("/")[0]
        image_domains = [
            mangabaka_domain,
            "mangabaka.dev",
            "cdn.mangabaka.dev", 
            "images.mangabaka.dev",
            "static.mangabaka.dev",
        ]
        img_sources = "'self' data: " + " ".join(f"https://{domain} http://{domain}" for domain in image_domains)
        return {
            "mangabaka_base": settings.MANGABAKA_BASE,
            "mangabaka_domain": mangabaka_domain,
            "image_domains": image_domains,
            "img_sources": img_sources,
            "cors_allow_origins": settings.CORS_ALLOW_ORIGINS,
        }
    
    # Debug endpoint for authentication and rate limiting
    @app.get("/api/debug/auth")
    async def debug_auth():
        """Debug endpoint to inspect authentication settings and clear rate limits."""
        # Clear rate limits for debugging
        app.state.rate_limits.clear()
        
        return {
            "auth_enabled": settings.AUTH_ENABLED,
            "auth_username": settings.AUTH_USERNAME,
            "auth_password_set": bool(settings.AUTH_PASSWORD),
            "auth_password_hashed": settings.AUTH_PASSWORD.startswith("$2b$") if settings.AUTH_PASSWORD else False,
            "auth_secret_key_set": bool(settings.AUTH_SECRET_KEY),
            "data_dir": str(settings.DATA_DIR),
            "rate_limits_cleared": True,
        }

    return app


# Only create app when running directly, not when importing
if __name__ == "__main__":
    app = create_app()
    # Run directly (no app_dir, no chdir, just pass the object)
    import uvicorn
    import os
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8999")),
        reload=False,
    )
else:
    # For testing, don't create app at import time
    # Tests will call create_app() directly
    app = None
