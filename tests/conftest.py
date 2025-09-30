# tests/conftest.py
import os
import sys
import importlib
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

# Add src to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(autouse=True)
def setup_test_environment():
    """Set up consistent test environment for all tests."""
    # Set default test environment variables
    test_data_dir = tempfile.mkdtemp(prefix="manganotify_test_")
    test_env = {
        "POLL_INTERVAL_SEC": "0",  # Disable polling
        "AUTH_ENABLED": "false",   # Disable auth by default
        "DATA_DIR": test_data_dir,
        "PUSHOVER_APP_TOKEN": "",
        "PUSHOVER_USER_KEY": "",
        "MANGABAKA_BASE": "https://api.mangabaka.dev",
        "LOG_LEVEL": "ERROR",  # Reduce log noise during tests
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")
    }
    
    # Store original values
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    # Clear any cached modules that might have old config
    modules_to_reload = [
        "manganotify.core.config",
        "manganotify.services.watchlist", 
        "manganotify.services.notifications",
        "manganotify.services.poller"
    ]
    
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    # Force reload the settings object
    if "manganotify.core.config" in sys.modules:
        config_module = sys.modules["manganotify.core.config"]
        if hasattr(config_module, 'settings'):
            # Create a new settings instance
            config_module.settings = config_module.create_settings()
    
    yield
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="manganotify_data_")
    os.environ["DATA_DIR"] = temp_dir
    return temp_dir


@pytest.fixture
def auth_enabled_app():
    """Create an app with authentication enabled for testing."""
    # Set auth environment variables
    auth_env = {
        "AUTH_ENABLED": "true",
        "AUTH_SECRET_KEY": "test-secret-key-12345678901234567890",
        "AUTH_USERNAME": "admin",
        "AUTH_PASSWORD": "password123",
        "AUTH_TOKEN_EXPIRE_HOURS": "24",
    }
    
    # Store original values
    original_env = {}
    for key, value in auth_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    # Reload config module
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])
    
    # Import and create app
    from manganotify.main import create_app
    app = create_app()
    
    yield app
    
    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def no_auth_app():
    """Create an app with authentication disabled for testing."""
    # Ensure auth is disabled
    os.environ["AUTH_ENABLED"] = "false"
    
    # Reload config module
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])
    
    # Import and create app
    from manganotify.main import create_app
    app = create_app()
    
    # Manually set up app state for testing (simulate lifespan context)
    from manganotify.core.config import create_settings
    import httpx
    app.state.client = httpx.AsyncClient(timeout=20.0)
    app.state.settings = create_settings()
    app.state.poller_task = None
    
    return app


@pytest.fixture
def patched_app(no_auth_app, temp_data_dir):
    """Create an app with patched settings for API testing."""
    from manganotify.core.config import create_settings
    test_settings = create_settings()
    
    # Patch the global settings to use the test data directory
    with patch('manganotify.services.watchlist.settings', test_settings), \
         patch('manganotify.services.notifications.settings', test_settings):
        yield no_auth_app
