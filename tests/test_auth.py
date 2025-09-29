# tests/test_auth.py
import importlib
import os
import sys
import pathlib
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from manganotify.main import create_app
from manganotify.auth import create_access_token, verify_token, authenticate_user


def _create_test_app(**env_vars):
    """Create test app with specific environment variables."""
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = str(value)
    
    # Also set default test environment variables
    import tempfile
    os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="manganotify_test_"))
    os.environ.setdefault("POLL_INTERVAL_SEC", "0")
    
    # Reload config module to pick up new environment variables
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])
    
    # Create app - it will pick up the new environment variables
    app = create_app()
    return app


def test_auth_disabled():
    """Test that auth is disabled by default."""
    # Explicitly set AUTH_ENABLED as string
    app = _create_test_app(AUTH_ENABLED="false")

    with TestClient(app) as client:
        # Auth status should show disabled
        r = client.get("/api/auth/status")
        assert r.status_code == 200
        assert r.json()["auth_enabled"] is False
        
        # Should be able to access protected endpoints without auth
        r = client.get("/api/watchlist")
        assert r.status_code == 200


def test_auth_enabled_no_creds():
    """Test auth enabled but no credentials provided."""
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="password123"
    )

    with TestClient(app) as client:
        # Auth status should show enabled
        r = client.get("/api/auth/status")
        assert r.status_code == 200
        assert r.json()["auth_enabled"] is True
        
        # Should not be able to access protected endpoints without auth
        r = client.get("/api/watchlist")
        assert r.status_code == 401


def test_login_success():
    """Test successful login."""
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="password123"
    )
    
    with TestClient(app) as client:
        # Login with correct credentials
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "password123"
        })
        assert r.status_code == 200
        
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
        
        # Use token to access protected endpoint
        token = data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        r = client.get("/api/watchlist", headers=headers)
        assert r.status_code == 200


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="password123"
    )
    
    with TestClient(app) as client:
        # Login with wrong password
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert r.status_code == 401
        
        # Login with wrong username
        r = client.post("/api/auth/login", json={
            "username": "wronguser",
            "password": "password123"
        })
        assert r.status_code == 401


def test_login_auth_disabled():
    """Test login when auth is disabled."""
    app = _create_test_app(AUTH_ENABLED=False)
    
    with TestClient(app) as client:
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "password123"
        })
        assert r.status_code == 400
        assert "Authentication is not enabled" in r.json()["detail"]


def test_get_me():
    """Test getting current user info."""
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="password123"
    )
    
    with TestClient(app) as client:
        # Login first
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "password123"
        })
        token = r.json()["access_token"]
        
        # Get user info
        headers = {"Authorization": f"Bearer {token}"}
        r = client.get("/api/auth/me", headers=headers)
        assert r.status_code == 200
        
        data = r.json()
        assert data["username"] == "admin"
        assert data["auth_enabled"] is True


def test_get_me_no_auth():
    """Test getting user info without authentication."""
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="password123"
    )
    
    with TestClient(app) as client:
        r = client.get("/api/auth/me")
        assert r.status_code == 401


def test_logout():
    """Test logout endpoint."""
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="password123"
    )
    
    with TestClient(app) as client:
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert "Logged out successfully" in r.json()["message"]


def test_token_verification():
    """Test JWT token verification."""
    # Test valid token by creating an app with auth enabled
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="testuser",
        AUTH_PASSWORD="password123"
    )
    
    with TestClient(app) as client:
        # Test valid token via login endpoint
        r = client.post("/api/auth/login", json={
            "username": "testuser",
            "password": "password123"
        })
        assert r.status_code == 200
        token = r.json()["access_token"]
        
        # Test token verification via /api/auth/me endpoint
        r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        user_data = r.json()
        assert user_data["username"] == "testuser"
        
        # Test invalid token
        r = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid-token"})
        assert r.status_code == 401


def test_authenticate_user():
    """Test user authentication."""
    # Test valid credentials by creating an app with auth enabled
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="password123"
    )
    
    with TestClient(app) as client:
        # Test valid credentials via login endpoint
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "password123"
        })
        assert r.status_code == 200
        
        # Test invalid credentials
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "wrongpassword"
        })
        assert r.status_code == 401
        
        r = client.post("/api/auth/login", json={
            "username": "wronguser",
            "password": "password123"
        })
        assert r.status_code == 401


def test_protected_endpoints():
    """Test that all protected endpoints require authentication."""
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="admin",
        AUTH_PASSWORD="password123"
    )
    
    with TestClient(app) as client:
        # Test various protected endpoints
        protected_endpoints = [
            ("GET", "/api/watchlist"),
            ("POST", "/api/watchlist"),
            ("DELETE", "/api/watchlist/1"),
            ("PATCH", "/api/watchlist/1/progress"),
            ("PATCH", "/api/watchlist/1/status"),
            ("POST", "/api/watchlist/1/read/next"),
            ("POST", "/api/watchlist/refresh"),
            ("GET", "/api/health/details"),
            ("GET", "/api/notifications"),
            ("DELETE", "/api/notifications"),
            ("POST", "/api/notify/test"),
            ("GET", "/api/discord/settings"),
            ("POST", "/api/discord/settings"),
            ("POST", "/api/discord/test"),
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                r = client.get(endpoint)
            elif method == "POST":
                r = client.post(endpoint, json={})
            elif method == "PATCH":
                r = client.patch(endpoint, json={})
            elif method == "DELETE":
                r = client.delete(endpoint)
            
            assert r.status_code == 401, f"Endpoint {method} {endpoint} should require auth"


def test_auth_with_custom_settings():
    """Test auth with custom username and token expiration."""
    app = _create_test_app(
        AUTH_ENABLED=True,
        AUTH_SECRET_KEY="test-secret-key-12345678901234567890",
        AUTH_USERNAME="customuser",
        AUTH_PASSWORD="custompass",
        AUTH_TOKEN_EXPIRE_HOURS=48
    )
    
    with TestClient(app) as client:
        # Login with custom username
        r = client.post("/api/auth/login", json={
            "username": "customuser",
            "password": "custompass"
        })
        assert r.status_code == 200
        
        data = r.json()
        assert data["expires_in"] == 48 * 3600  # 48 hours in seconds
