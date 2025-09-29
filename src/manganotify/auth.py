# src/manganotify/auth.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if not settings.AUTH_SECRET_KEY:
        raise ValueError("AUTH_SECRET_KEY is required for JWT token creation")
    
    if len(settings.AUTH_SECRET_KEY) < 32:
        raise ValueError("AUTH_SECRET_KEY must be at least 32 characters long for security")
    
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.AUTH_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({"exp": expire.timestamp()})
    encoded_jwt = jwt.encode(to_encode, settings.AUTH_SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token."""
    if not settings.AUTH_SECRET_KEY:
        logger.error("AUTH_SECRET_KEY is not set - cannot verify token")
        return None
    
    try:
        # First decode header to check algorithm
        unverified_header = jwt.get_unverified_header(token)
        if unverified_header.get("alg") != "HS256":
            logger.warning("JWT token uses invalid algorithm: %s", unverified_header.get("alg"))
            return None
        
        # Then decode with algorithm validation
        payload = jwt.decode(token, settings.AUTH_SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            return None
        return {"username": username}
    except jwt.PyJWTError as e:
        logger.warning("JWT token verification failed: %s", e)
        return None


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[dict]:
    """Get current user from JWT token."""
    if not settings.AUTH_ENABLED:
        return {"username": "anonymous"}
    
    if not credentials:
        return None
    
    user = verify_token(credentials.credentials)
    if user is None:
        return None
    
    return user


async def require_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    """Require authentication and return user info."""
    if not settings.AUTH_ENABLED:
        return {"username": "anonymous"}
    
    user = await get_current_user(credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate a user with username and password."""
    if not settings.AUTH_ENABLED:
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
    if username != settings.AUTH_USERNAME:
        logger.debug(f"Username mismatch: '{username}' != '{settings.AUTH_USERNAME}'")
        return False
    
    # If AUTH_PASSWORD is empty, it means no password is set (insecure)
    if not settings.AUTH_PASSWORD:
        logger.error("AUTH_PASSWORD is not set - authentication disabled for security")
        return False
    
    # Check if stored password is already hashed (starts with $2b$)
    if settings.AUTH_PASSWORD.startswith("$2b$"):
        # Password is already hashed, verify against hash
        result = verify_password(password, settings.AUTH_PASSWORD)
        logger.debug(f"Password hash verification: {result}")
        return result
    else:
        # Password is plain text (legacy), hash it and compare
        logger.warning("AUTH_PASSWORD appears to be plain text - consider hashing it")
        result = password == settings.AUTH_PASSWORD
        logger.debug(f"Password plain text comparison: {result}")
        return result
