# src/manganotify/routers/auth.py
from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from ..auth import (
    authenticate_user,
    create_access_token,
    require_auth,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserInfo(BaseModel):
    username: str
    auth_enabled: bool


@router.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, req: Request):
    """Login endpoint."""
    # Get settings from app state
    settings = req.app.state.settings

    if not settings.AUTH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication is not enabled",
        )

    if not authenticate_user(request.username, request.password, settings):
        logger.warning("Failed login attempt for username: %s", request.username)
        # Add delay to prevent brute force attacks
        import asyncio

        await asyncio.sleep(1)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(hours=settings.AUTH_TOKEN_EXPIRE_HOURS)
    access_token = create_access_token(
        data={"sub": request.username},
        expires_delta=access_token_expires,
        settings_obj=settings,
    )

    logger.info("Successful login for username: %s", request.username)
    return LoginResponse(
        access_token=access_token, expires_in=int(access_token_expires.total_seconds())
    )


@router.get("/api/auth/me", response_model=UserInfo)
async def get_current_user_info(
    current_user: dict = Depends(require_auth), req: Request = None
):
    """Get current user information."""
    # Get settings from app state
    settings = req.app.state.settings

    return UserInfo(
        username=current_user["username"], auth_enabled=settings.AUTH_ENABLED
    )


@router.post("/api/auth/logout")
async def logout():
    """Logout endpoint (client-side token removal)."""
    return {"message": "Logged out successfully"}


@router.get("/api/auth/status")
async def auth_status(req: Request):
    """Check if authentication is enabled."""
    # Get settings from app state
    settings = req.app.state.settings

    return {"auth_enabled": settings.AUTH_ENABLED}
