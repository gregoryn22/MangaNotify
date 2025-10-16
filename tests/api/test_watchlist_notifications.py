"""Tests related to watchlist notification isolation."""

import json
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(patched_app):
    """Return a FastAPI test client with patched settings."""
    return TestClient(patched_app)


def test_toggling_notifications_does_not_affect_other_series(client, temp_data_dir, monkeypatch):
    """Toggling notifications for one series should not change other series."""

    async def fake_api_series_by_id(client, series_id, full=True):  # pragma: no cover - simple stub
        return {"data": {"id": series_id, "title": f"Series {series_id}", "total_chapters": 10}}

    # Ensure external API calls are stubbed out for repeatable tests
    monkeypatch.setattr(
        "manganotify.routers.watchlist.api_series_by_id",
        fake_api_series_by_id,
    )

    # Add two series to the watchlist
    for series_id in (1, 2):
        response = client.post(
            "/api/watchlist",
            json={
                "id": series_id,
                "title": f"Series {series_id}",
                "total_chapters": 10,
            },
        )
        assert response.status_code == 200

    # Disable notifications for the first series
    response = client.patch(
        "/api/watchlist/1/notifications",
        json={"enabled": False, "pushover": False},
    )
    assert response.status_code == 200

    watchlist_path = os.path.join(temp_data_dir, "watchlist.json")
    with open(watchlist_path, "r", encoding="utf-8") as f:
        watchlist = json.load(f)

    series_one = next(item for item in watchlist if item["id"] == 1)
    series_two = next(item for item in watchlist if item["id"] == 2)

    assert series_one["notifications"]["enabled"] is False
    assert series_one["notifications"]["pushover"] is False

    # Series two should still have the default notification settings
    assert series_two["notifications"]["enabled"] is True
    assert series_two["notifications"]["pushover"] is True
