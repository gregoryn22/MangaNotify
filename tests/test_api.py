# tests/test_api.py
import importlib, os, sys, pathlib
import os
import sys

import respx
from fastapi.testclient import TestClient

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

# Updated to use main.py instead of server.py
srv = importlib.import_module("manganotify.main")
importlib.reload(srv)

def _reload_with_env(monkeypatch, **env):
    """
    Set env vars and reload modules so they pick them up.
    We explicitly set all Pushover keys to "" unless provided,
    so python-dotenv will NOT overwrite them from .env.
    """
    # Defaults for all Pushover variants (empty strings = falsy, and block dotenv override)
    defaults = {
        "PUSHOVER_APP_TOKEN": "",
        "PUSHOVER_TOKEN": "",
        "PUSHOVER_USER_KEY": "",
        "PUSHOVER_USER": "",
        # Make sure polling doesn't start during tests
        "POLL_INTERVAL_SEC": "0",
        # Disable auth for most tests
        "AUTH_ENABLED": "false",
    }

    # Apply defaults first
    for k, v in defaults.items():
        monkeypatch.setenv(k, v)

    # Then apply test-specific overrides
    for key, val in env.items():
        if val is None:
            # Keep as empty string to remain falsy and prevent dotenv override
            monkeypatch.setenv(key, "")
        else:
            monkeypatch.setenv(key, str(val))

    # Ensure DATA_DIR exists if provided
    data_dir = os.getenv("DATA_DIR")
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

    # Reload config module to pick up new environment variables
    if "manganotify.core.config" in sys.modules:
        importlib.reload(sys.modules["manganotify.core.config"])
    
    # Reload main module
    if "manganotify.main" in sys.modules:
        importlib.reload(sys.modules["manganotify.main"])
    
    return sys.modules["manganotify.main"]


def test_notify_test_missing_creds(tmp_path, monkeypatch):
    # No Pushover creds; disable poller; disable auth for test
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PUSHOVER_APP_TOKEN", "")
    monkeypatch.setenv("PUSHOVER_USER_KEY", "")
    monkeypatch.setenv("POLL_INTERVAL_SEC", "0")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    
    # Import and create app
    from manganotify.main import create_app
    app = create_app()

    # Use context manager so lifespan runs
    with TestClient(app) as client:
        r = client.post("/api/notify/test")
        # server returns 500 for missing creds (by design)
        assert r.status_code == 500
        js = r.json()
        assert js.get("ok") is False
        assert "Missing Pushover env vars" in js.get("message", "")


def test_notify_test_ok(tmp_path, monkeypatch):
    # Provide creds; disable poller for determinism; disable auth for test
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PUSHOVER_APP_TOKEN", "tokenX")
    monkeypatch.setenv("PUSHOVER_USER_KEY", "userY")
    monkeypatch.setenv("POLL_INTERVAL_SEC", "0")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    
    # Import and create app
    from manganotify.main import create_app
    app = create_app()

    with TestClient(app) as client:
        # Mock the external Pushover API call
        with respx.mock(assert_all_called=True) as router:
            router.post("https://api.pushover.net/1/messages.json").respond(
                200, json={"status": 1, "request": "abc123"}
            )
            r = client.post("/api/notify/test")

        assert r.status_code == 200
        js = r.json()
        assert js.get("ok") is True
        assert js.get("raw", {}).get("status") == 1  # Check the Pushover API response status
        assert "raw" in js
