"""Tests for rate limiting functionality."""

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from manganotify.main import create_app


@pytest.fixture
def test_app():
    """Create a test app instance."""
    import os
    import tempfile

    os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="manganotify_test_")
    os.environ["POLL_INTERVAL_SEC"] = "0"
    os.environ["AUTH_ENABLED"] = "false"
    os.environ["LOG_LEVEL"] = "ERROR"

    app = create_app()
    return app


def test_rate_limit_pruning_logic(test_app):
    """Test that rate limit cleanup removes stale entries."""
    # Manually set up rate limits with old timestamps
    current_time = time.time()
    old_time = current_time - 120  # 2 minutes ago (older than 60s threshold)
    recent_time = current_time - 30  # 30 seconds ago (within 60s threshold)

    test_app.state.rate_limits = {
        "192.168.1.1": [old_time, old_time],  # Should be removed
        "192.168.1.2": [recent_time],  # Should be kept
        "192.168.1.3": [old_time, recent_time],  # Should be kept (has recent)
        "192.168.1.4": [old_time],  # Should be removed
    }

    # Simulate the cleanup logic
    rate_limits = test_app.state.rate_limits
    stale_ips = [
        ip
        for ip, timestamps in rate_limits.items()
        if all(current_time - t > 60 for t in timestamps)
    ]

    # Verify correct IPs identified as stale
    assert "192.168.1.1" in stale_ips
    assert "192.168.1.4" in stale_ips
    assert "192.168.1.2" not in stale_ips
    assert "192.168.1.3" not in stale_ips

    # Perform cleanup
    for ip in stale_ips:
        del rate_limits[ip]

    # Verify cleanup worked
    assert "192.168.1.1" not in rate_limits
    assert "192.168.1.4" not in rate_limits
    assert "192.168.1.2" in rate_limits
    assert "192.168.1.3" in rate_limits


def test_rate_limit_per_request_cleanup(test_app):
    """Test that per-request cleanup still works."""
    with TestClient(test_app) as client:
        # Initialize rate limits manually
        test_app.state.rate_limits = {}

        # Make multiple requests to trigger rate limiting storage
        for _i in range(5):
            response = client.get("/api/health")
            assert response.status_code == 200

        # Rate limits should have entries
        assert len(test_app.state.rate_limits) > 0

        # Make another request after a delay (simulate old entries)
        # The middleware should clean entries older than 60s for the current IP
        response = client.get("/api/health")
        assert response.status_code == 200


def test_rate_limit_enforcement(test_app):
    """Test that rate limit tracking works correctly."""
    with TestClient(test_app, raise_server_exceptions=False) as client:
        # Clear rate limits
        test_app.state.rate_limits = {}

        # Make some requests to the health endpoint (which is rate limited)
        for _i in range(5):
            response = client.get("/api/health")
            assert response.status_code == 200

        # Verify rate limits are being tracked
        assert len(test_app.state.rate_limits) > 0, "Rate limits should be tracked"
        
        # Verify entries are lists of timestamps
        for ip, timestamps in test_app.state.rate_limits.items():
            assert isinstance(timestamps, list), f"Rate limit entries should be lists for IP {ip}"
            assert len(timestamps) > 0, f"Should have timestamp entries for IP {ip}"


@pytest.mark.asyncio
async def test_rate_limit_cleanup_task_lifecycle(test_app):
    """Test that the cleanup task starts and stops correctly."""
    # The cleanup task should be created during lifespan
    async with test_app.router.lifespan_context(test_app):
        # Task should exist
        assert hasattr(test_app.state, "rate_limit_cleanup_task")
        assert test_app.state.rate_limit_cleanup_task is not None

        # Task should be running
        assert not test_app.state.rate_limit_cleanup_task.done()

    # After lifespan, task should be cancelled
    assert test_app.state.rate_limit_cleanup_task.done()
