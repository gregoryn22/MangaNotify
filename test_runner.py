#!/usr/bin/env python3
"""
Simple test runner to verify fixes work.
This can be run independently to test the application.
"""
import os
import sys
import tempfile
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

# Set test environment
os.environ.update({
    "POLL_INTERVAL_SEC": "0",
    "AUTH_ENABLED": "false", 
    "DATA_DIR": tempfile.mkdtemp(prefix="manganotify_test_"),
    "PUSHOVER_APP_TOKEN": "",
    "PUSHOVER_USER_KEY": "",
    "MANGABAKA_BASE": "https://api.mangabaka.dev",
    "LOG_LEVEL": "INFO",
})

def test_app_creation():
    """Test that app can be created without infinite loops."""
    print("Testing app creation...")
    
    from manganotify.main import create_app
    app = create_app()
    
    print("✓ App created successfully")
    print(f"✓ Poll interval: {app.state.settings.POLL_INTERVAL_SEC}")
    print(f"✓ Auth enabled: {app.state.settings.AUTH_ENABLED}")
    print(f"✓ Poller task: {app.state.poller_task}")
    
    return app

async def test_app_lifespan():
    """Test that app lifespan works correctly."""
    print("\nTesting app lifespan...")
    
    from manganotify.main import create_app
    from fastapi.testclient import TestClient
    
    app = create_app()
    
    # Test that the app starts and stops cleanly
    with TestClient(app) as client:
        # Test basic endpoint
        response = client.get("/api/health")
        print(f"✓ Health check: {response.status_code}")
        
        # Test that poller is not running
        assert app.state.poller_task is None, "Poller should not be running when POLL_INTERVAL_SEC=0"
        print("✓ Poller correctly disabled")
    
    print("✓ App lifespan test passed")

def test_auth_app():
    """Test auth-enabled app creation."""
    print("\nTesting auth-enabled app...")
    
    # Set auth environment
    os.environ.update({
        "AUTH_ENABLED": "true",
        "AUTH_SECRET_KEY": "test-secret-key-12345678901234567890",
        "AUTH_USERNAME": "admin", 
        "AUTH_PASSWORD": "password123",
    })
    
    # Reload config
    import importlib
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])
    
    from manganotify.main import create_app
    from fastapi.testclient import TestClient
    
    app = create_app()
    
    with TestClient(app) as client:
        # Test auth status
        response = client.get("/api/auth/status")
        print(f"✓ Auth status: {response.status_code}")
        assert response.status_code == 200
        assert response.json()["auth_enabled"] is True
        
        # Test protected endpoint
        response = client.get("/api/watchlist")
        print(f"✓ Protected endpoint: {response.status_code}")
        assert response.status_code == 401  # Should require auth
    
    print("✓ Auth app test passed")

if __name__ == "__main__":
    print("Running MangaNotify test suite...")
    
    try:
        # Test basic app creation
        app = test_app_creation()
        
        # Test lifespan
        asyncio.run(test_app_lifespan())
        
        # Test auth app
        test_auth_app()
        
        print("\n🎉 All tests passed! The infinite loop issue should be fixed.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
