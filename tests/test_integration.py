# tests/test_integration.py
import importlib
import os
import sys
import pathlib
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from manganotify.main import create_app


def test_full_auth_flow():
    """Test complete authentication flow with watchlist operations."""
    # Create app with auth enabled
    os.environ.update({
        "AUTH_ENABLED": "true",
        "AUTH_SECRET_KEY": "test-secret-key-12345678901234567890",
        "AUTH_USERNAME": "admin",
        "AUTH_PASSWORD": "password123",
        "DATA_DIR": "/tmp/test_data",
        "POLL_INTERVAL_SEC": "0"
    })
    
    # Reload the config module to pick up new environment variables
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])
    
    app = create_app()
    
    with TestClient(app) as client:
        # 1. Check auth status
        r = client.get("/api/auth/status")
        assert r.status_code == 200
        assert r.json()["auth_enabled"] is True
        
        # 2. Try to access protected endpoint without auth (should fail)
        r = client.get("/api/watchlist")
        assert r.status_code == 401
        
        # 3. Login
        r = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "password123"
        })
        assert r.status_code == 200
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 4. Access protected endpoints with auth (should succeed)
        r = client.get("/api/watchlist", headers=headers)
        assert r.status_code == 200
        
        r = client.get("/api/auth/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["username"] == "admin"
        
        # 5. Logout (client-side only - token remains valid until expiration)
        r = client.post("/api/auth/logout")
        assert r.status_code == 200
        assert "Logged out successfully" in r.json()["message"]
        
        # 6. Token should still be valid (JWT tokens are stateless)
        # In a real application, you'd need a token blacklist or shorter expiration
        r = client.get("/api/watchlist", headers=headers)
        assert r.status_code == 200  # Token is still valid


def test_auth_disabled_full_access():
    """Test that when auth is disabled, all endpoints are accessible."""
    os.environ.update({
        "AUTH_ENABLED": "false",
        "DATA_DIR": "/tmp/test_data",
        "POLL_INTERVAL_SEC": "0"
    })
    
    # Reload config module to pick up new environment variables
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])
    
    app = create_app()
    
    with TestClient(app) as client:
        # All endpoints should be accessible without auth
        endpoints = [
            ("GET", "/api/watchlist"),
            ("GET", "/api/auth/status"),
            ("GET", "/api/health"),
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                r = client.get(endpoint)
            assert r.status_code == 200, f"Endpoint {endpoint} should be accessible when auth is disabled"


def test_cors_with_auth():
    """Test CORS headers work with authentication."""
    os.environ.update({
        "AUTH_ENABLED": "true",
        "AUTH_SECRET_KEY": "test-secret-key-12345678901234567890",
        "AUTH_USERNAME": "admin",
        "AUTH_PASSWORD": "password123",
        "CORS_ALLOW_ORIGINS": "https://example.com,http://localhost:3000",
        "DATA_DIR": "/tmp/test_data",
        "POLL_INTERVAL_SEC": "0"
    })

    # Reload config module to pick up new environment variables
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])

    app = create_app()
    
    with TestClient(app) as client:
        # Test CORS preflight request
        r = client.options("/api/watchlist", headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization"
        })
        assert r.status_code == 200
        assert "Access-Control-Allow-Origin" in r.headers
        
        # Test actual request with CORS headers
        r = client.get("/api/watchlist", headers={
            "Origin": "https://example.com"
        })
        assert r.status_code == 401  # Should fail due to auth, not CORS
        assert "Access-Control-Allow-Origin" in r.headers


def test_error_handling():
    """Test error handling in auth endpoints."""
    os.environ.update({
        "AUTH_ENABLED": "true",
        "AUTH_SECRET_KEY": "test-secret-key-12345678901234567890",
        "AUTH_USERNAME": "admin",
        "AUTH_PASSWORD": "password123",
        "DATA_DIR": "/tmp/test_data",
        "POLL_INTERVAL_SEC": "0"
    })
    
    # Reload config module to pick up new environment variables
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])
    
    app = create_app()
    
    with TestClient(app) as client:
        # Test malformed login request
        r = client.post("/api/auth/login", json={
            "username": "admin"
            # Missing password
        })
        assert r.status_code == 422  # Validation error
        
        # Test invalid JSON
        r = client.post("/api/auth/login", data="invalid json")
        assert r.status_code == 422
        
        # Test empty request
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 422


def test_token_expiration():
    """Test token expiration handling."""
    import time
    from manganotify.auth import create_access_token
    from datetime import timedelta

    os.environ.update({
        "AUTH_ENABLED": "true",
        "AUTH_SECRET_KEY": "test-secret-key-12345678901234567890",
        "AUTH_USERNAME": "admin",
        "AUTH_PASSWORD": "password123",
        "DATA_DIR": "/tmp/test_data",
        "POLL_INTERVAL_SEC": "0"
    })

    # Reload config module to pick up new environment variables
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])

    app = create_app()
    
    with TestClient(app) as client:
        # Get the test settings from the app
        test_settings = app.state.settings
        
        # Create a token that expires immediately
        expired_token = create_access_token(
            {"sub": "admin"}, 
            expires_delta=timedelta(seconds=-1),  # Already expired
            settings_obj=test_settings
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        r = client.get("/api/watchlist", headers=headers)
        assert r.status_code == 401  # Should fail due to expired token
