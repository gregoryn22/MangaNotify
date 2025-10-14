# src/manganotify/auth.py
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from .core.config import settings

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token security
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict, expires_delta: timedelta | None = None, settings_obj=None
) -> str:
    """Create a JWT access token."""
    # Use provided settings or fall back to imported settings
    if settings_obj is None:
        settings_obj = settings

    if not settings_obj.AUTH_SECRET_KEY:
        raise ValueError("AUTH_SECRET_KEY is required for JWT token creation")

    if len(settings_obj.AUTH_SECRET_KEY) < 32:
        raise ValueError(
            "AUTH_SECRET_KEY must be at least 32 characters long for security"
        )

    # Validate data contains required fields
    if "sub" not in data:
        raise ValueError("Token data must contain 'sub' field")

    # Validate username format
    username = data.get("sub", "")
    if not username or len(username) < 3 or len(username) > 50:
        raise ValueError("Username must be between 3 and 50 characters")

    if not username.replace("_", "").replace("-", "").isalnum():
        raise ValueError("Username contains invalid characters")

    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            hours=settings_obj.AUTH_TOKEN_EXPIRE_HOURS
        )

    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, settings_obj.AUTH_SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str, settings_obj=None) -> dict | None:
    """Verify and decode a JWT token."""
    # Use provided settings or fall back to imported settings
    if settings_obj is None:
        settings_obj = settings

    if not settings_obj.AUTH_SECRET_KEY:
        logger.error("AUTH_SECRET_KEY is not set - cannot verify token")
        return None

    try:
        # First decode header to check algorithm
        unverified_header = jwt.get_unverified_header(token)
        if unverified_header.get("alg") != "HS256":
            logger.warning(
                "JWT token uses invalid algorithm: %s", unverified_header.get("alg")
            )
            return None

        # Then decode with algorithm validation
        payload = jwt.decode(token, settings_obj.AUTH_SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            return None
        return {"username": username}
    except jwt.PyJWTError as e:
        logger.warning("JWT token verification failed: %s", e)
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = None, settings_obj=None
) -> dict | None:
    """Get current user from JWT token."""
    # Use provided settings or fall back to imported settings
    if settings_obj is None:
        settings_obj = settings

    if not settings_obj.AUTH_ENABLED:
        return {"username": "anonymous"}

    if not credentials:
        return None

    user = verify_token(credentials.credentials, settings_obj)
    if user is None:
        return None

    return user


async def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Require authentication and return user info."""
    # Get settings from app state
    app_settings = request.app.state.settings

    if not app_settings.AUTH_ENABLED:
        return {"username": "anonymous"}

    user = await get_current_user(credentials, app_settings)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def authenticate_user(username: str, password: str, settings_obj=None) -> bool:
    """Authenticate a user with username and password."""
    # Use provided settings or fall back to imported settings
    if settings_obj is None:
        settings_obj = settings

    if not settings_obj.AUTH_ENABLED:
        logger.debug("Authentication disabled")
        return False

    # Validate input parameters
    if not username or not password:
        logger.debug("Missing username or password")
        return False

    # Validate username length and format
    if len(username) < 3 or len(username) > 50:
        logger.debug(f"Username length invalid: {len(username)}")
        return False

    if not username.replace("_", "").replace("-", "").isalnum():
        logger.debug(f"Username format invalid: {username}")
        return False

    # Validate password length
    if len(password) < 8 or len(password) > 128:
        logger.debug(f"Password length invalid: {len(password)}")
        return False

    # Hash the provided password and compare with stored hash
    if username != settings_obj.AUTH_USERNAME:
        logger.debug(
            f"Username mismatch: '{username}' != '{settings_obj.AUTH_USERNAME}'"
        )
        return False

    # If AUTH_PASSWORD is empty, it means no password is set (insecure)
    if not settings_obj.AUTH_PASSWORD:
        logger.error("AUTH_PASSWORD is not set - authentication disabled for security")
        return False

    # Check if stored password is already hashed (starts with $2b$)
    if settings_obj.AUTH_PASSWORD.startswith("$2b$"):
        # Password is already hashed, verify against hash
        result = verify_password(password, settings_obj.AUTH_PASSWORD)
        logger.debug(f"Password hash verification: {result}")
        return result
    else:
        # Password is plain text (legacy), hash it and compare
        logger.warning("AUTH_PASSWORD appears to be plain text - consider hashing it")
        result = password == settings_obj.AUTH_PASSWORD
        logger.debug(f"Password plain text comparison: {result}")
        return result
