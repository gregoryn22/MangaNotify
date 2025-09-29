# src/manganotify/routers/setup.py
"""
Setup wizard for secure credential configuration.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.crypto import encrypt_credential, decrypt_credential, generate_master_key
from ..auth import get_password_hash, require_auth

logger = logging.getLogger(__name__)

router = APIRouter()

class SetupStatus(BaseModel):
    """Current setup status."""
    is_configured: bool
    auth_enabled: bool
    has_credentials: bool
    missing_items: list[str]

class SetupRequest(BaseModel):
    """Setup configuration request."""
    # Authentication
    auth_enabled: bool = Field(default=True, description="Enable authentication")
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$", description="Admin username (alphanumeric, underscore, hyphen only)")
    password: str = Field(..., min_length=8, max_length=128, description="Admin password (min 8 chars, max 128)")
    
    # Notification credentials (optional)
    pushover_app_token: Optional[str] = Field(default=None, max_length=100, description="Pushover app token")
    pushover_user_key: Optional[str] = Field(default=None, max_length=100, description="Pushover user key")
    discord_webhook_url: Optional[str] = Field(default=None, max_length=500, pattern=r"^https://discord\.com/api/webhooks/\d+/[a-zA-Z0-9_-]+$", description="Discord webhook URL")
    
    # Master key for encryption (optional, will be generated if not provided)
    master_key: Optional[str] = Field(default=None, min_length=32, max_length=100, description="Master encryption key")

class SetupResponse(BaseModel):
    """Setup response with generated configuration."""
    success: bool
    message: str
    env_config: dict[str, str]
    master_key: Optional[str] = None

@router.get("/api/setup/status")
async def get_setup_status(current_user: dict = Depends(require_auth)) -> SetupStatus:
    """Get current setup status."""
    missing_items = []
    
    # Check authentication setup
    if settings.AUTH_ENABLED:
        if not settings.AUTH_SECRET_KEY:
            missing_items.append("AUTH_SECRET_KEY")
        if not settings.AUTH_PASSWORD:
            missing_items.append("AUTH_PASSWORD")
        if not settings.AUTH_USERNAME:
            missing_items.append("AUTH_USERNAME")
    
    # Check notification credentials
    has_credentials = bool(
        settings.PUSHOVER_APP_TOKEN or 
        settings.PUSHOVER_USER_KEY or 
        settings.DISCORD_WEBHOOK_URL
    )
    
    # Determine if configuration is complete
    if settings.AUTH_ENABLED:
        is_configured = (
            settings.AUTH_SECRET_KEY and 
            settings.AUTH_PASSWORD and 
            settings.AUTH_USERNAME and
            len(missing_items) == 0
        )
    else:
        is_configured = True  # No auth required, so it's configured
    
    return SetupStatus(
        is_configured=is_configured,
        auth_enabled=settings.AUTH_ENABLED,
        has_credentials=has_credentials,
        missing_items=missing_items
    )

@router.post("/api/setup/configure", response_model=SetupResponse)
async def configure_setup(request: SetupRequest, current_user: dict = Depends(require_auth)) -> SetupResponse:
    """Configure the application with secure credentials."""
    
    # Additional security validation
    if request.auth_enabled:
        # Check for common weak passwords
        weak_passwords = ["password", "12345678", "admin", "qwerty", "letmein", "welcome", "password123", "123456789", "manganotify", "manga"]
        if request.password.lower() in weak_passwords:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too weak. Please choose a stronger password."
            )
        
        # Check password complexity
        if len(request.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Check for password patterns
        if request.password.lower() == request.username.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password cannot be the same as username"
            )
        
        # Check username doesn't contain sensitive terms
        sensitive_usernames = ["admin", "root", "administrator", "user", "test"]
        if request.username.lower() in sensitive_usernames:
            logger.warning("User chose potentially sensitive username: %s", request.username)
        
        # Validate username format
        if not request.username.replace("_", "").replace("-", "").isalnum():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must contain only alphanumeric characters, underscores, and hyphens"
            )
        
        # Check username length
        if len(request.username) < 3 or len(request.username) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be between 3 and 50 characters"
            )
    
    # Validate notification credentials
    if request.pushover_app_token and len(request.pushover_app_token) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pushover app token appears to be too short"
        )
    
    if request.pushover_user_key and len(request.pushover_user_key) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pushover user key appears to be too short"
        )
    
    if request.discord_webhook_url and not request.discord_webhook_url.startswith("https://discord.com/api/webhooks/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discord webhook URL must start with https://discord.com/api/webhooks/"
        )
    
    # Validate master key if provided
    if request.master_key and len(request.master_key) < 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Master key must be at least 32 characters long"
        )
    
    # Validate master key format
    if request.master_key and not request.master_key.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Master key must contain only alphanumeric characters, underscores, and hyphens"
        )
    
    # Generate master key if not provided
    master_key = request.master_key or generate_master_key()
    
    # Prepare environment configuration
    env_config = {}
    
    # Authentication configuration
    if request.auth_enabled:
        env_config["AUTH_ENABLED"] = "true"
        env_config["AUTH_USERNAME"] = request.username
        env_config["AUTH_PASSWORD"] = get_password_hash(request.password)
        env_config["AUTH_SECRET_KEY"] = generate_master_key()  # Different key for JWT
        env_config["AUTH_TOKEN_EXPIRE_HOURS"] = "24"
    else:
        env_config["AUTH_ENABLED"] = "false"
    
    # Encrypt notification credentials if provided
    if request.pushover_app_token:
        env_config["PUSHOVER_APP_TOKEN"] = encrypt_credential(request.pushover_app_token, master_key)
    if request.pushover_user_key:
        env_config["PUSHOVER_USER_KEY"] = encrypt_credential(request.pushover_user_key, master_key)
    if request.discord_webhook_url:
        env_config["DISCORD_WEBHOOK_URL"] = encrypt_credential(request.discord_webhook_url, master_key)
        env_config["DISCORD_ENABLED"] = "true"
    
    # Add other recommended settings
    env_config["CORS_ALLOW_ORIGINS"] = "https://yourdomain.com"  # User MUST change this in production
    env_config["LOG_LEVEL"] = "INFO"
    env_config["LOG_FORMAT"] = "plain"
    env_config["POLL_INTERVAL_SEC"] = "1800"
    env_config["PORT"] = "8999"
    
    logger.info("Setup configuration completed successfully")
    
    return SetupResponse(
        success=True,
        message="Configuration generated successfully. Save these values to your .env file.",
        env_config=env_config,
        master_key=master_key
    )

@router.get("/api/setup/test-credentials")
async def test_credentials(
    pushover_app_token: Optional[str] = None,
    pushover_user_key: Optional[str] = None,
    discord_webhook_url: Optional[str] = None,
    master_key: Optional[str] = None,
    current_user: dict = Depends(require_auth)
):
    """Test notification credentials before saving."""
    import httpx
    
    results = {}
    
    # Test Pushover credentials
    if pushover_app_token and pushover_user_key:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.pushover.net/1/messages.json",
                    data={
                        "token": pushover_app_token,
                        "user": pushover_user_key,
                        "title": "MangaNotify Test",
                        "message": "This is a test notification from MangaNotify setup."
                    },
                    timeout=10.0
                )
                results["pushover"] = {
                    "success": r.status_code == 200,
                    "status": r.status_code,
                    "response": r.json() if r.status_code == 200 else None
                }
        except Exception as e:
            results["pushover"] = {"success": False, "error": str(e)}
    
    # Test Discord webhook
    if discord_webhook_url:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    discord_webhook_url,
                    json={
                        "content": "🔔 **MangaNotify Test**\nThis is a test notification from MangaNotify setup."
                    },
                    timeout=10.0
                )
                results["discord"] = {
                    "success": r.status_code in [200, 204],
                    "status": r.status_code
                }
        except Exception as e:
            results["discord"] = {"success": False, "error": str(e)}
    
    return {"results": results}

@router.get("/api/setup/generate-env")
async def generate_env_file(current_user: dict = Depends(require_auth)):
    """Generate a sample .env file with secure defaults."""
    sample_env = """# MangaNotify Configuration
# Generated by setup wizard

# Authentication (REQUIRED)
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=$2b$12$...  # Use setup wizard to generate this
AUTH_SECRET_KEY=...  # Use setup wizard to generate this
AUTH_TOKEN_EXPIRE_HOURS=24

# CORS (SECURITY WARNING: Change "*" in production!)
CORS_ALLOW_ORIGINS=*

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=plain

# Polling
POLL_INTERVAL_SEC=1800
PORT=8999

# Data storage
DATA_DIR=./data

# Notifications (optional - encrypted)
PUSHOVER_APP_TOKEN=...  # Encrypted with master key
PUSHOVER_USER_KEY=...    # Encrypted with master key
DISCORD_WEBHOOK_URL=...  # Encrypted with master key
DISCORD_ENABLED=false

# Master encryption key (KEEP SECURE!)
MASTER_KEY=...  # Generated by setup wizard
"""
    
    return {"env_content": sample_env}
