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
    Set env vars and reload `server` so it picks them up.
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

    # Fresh import of main.py with new env
    if "manganotify.main" in sys.modules:
        del sys.modules["manganotify.main"]
    srv = importlib.import_module("manganotify.main")
    importlib.reload(srv)
    return srv


def test_notify_test_missing_creds(tmp_path, monkeypatch):
    # No Pushover creds; disable poller
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    srv = _reload_with_env(
        monkeypatch,
        PUSHOVER_APP_TOKEN=None,  # stays ""
        PUSHOVER_USER_KEY=None,   # stays ""
        POLL_INTERVAL_SEC="0",
    )

    # Use context manager so lifespan runs
    with TestClient(srv.create_app()) as client:
        r = client.post("/api/notify/test")
        # server returns 500 for missing creds (by design)
        assert r.status_code == 500
        js = r.json()
        assert js.get("ok") is False
        assert "Missing Pushover env vars" in js.get("message", "")


def test_notify_test_ok(tmp_path, monkeypatch):
    # Provide creds; disable poller for determinism
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    srv = _reload_with_env(
        monkeypatch,
        PUSHOVER_APP_TOKEN="tokenX",
        PUSHOVER_USER_KEY="userY",
        POLL_INTERVAL_SEC="0",
    )

    with TestClient(srv.create_app()) as client:
        # Mock the external Pushover API call
        with respx.mock(assert_all_called=True) as router:
            router.post("https://api.pushover.net/1/messages.json").respond(
                200, json={"status": 1, "request": "abc123"}
            )
            r = client.post("/api/notify/test")

        assert r.status_code == 200
        js = r.json()
        assert js.get("ok") is True
        assert js.get("pushover_status") == 1
        assert "who" in js and "token" in js["who"] and "user" in js["who"]
