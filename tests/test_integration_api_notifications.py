"""Integration-style tests for poller/notification behaviour without live HTTP calls."""

from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
import respx
from httpx import Response

from manganotify.core.config import create_settings
from manganotify.services.notifications import load_notifications
from manganotify.services.poller import process_once
from manganotify.services.watchlist import load_watchlist, save_watchlist


@pytest.fixture
def isolated_settings(tmp_path, monkeypatch):
    settings = create_settings()
    settings.DATA_DIR = Path(tmp_path)
    monkeypatch.setattr("manganotify.services.watchlist.settings", settings, raising=False)
    monkeypatch.setattr("manganotify.services.notifications.settings", settings, raising=False)
    monkeypatch.setattr("manganotify.services.poller.settings", settings, raising=False)
    return settings


@pytest.fixture
def fake_notifiers(monkeypatch):
    calls = {"pushover": [], "discord": []}

    async def fake_pushover(client, title, message):
        calls["pushover"].append((title, message))
        return {"ok": True}

    async def fake_discord(client, title, message):
        calls["discord"].append((title, message))
        return {"ok": True}

    monkeypatch.setattr("manganotify.services.poller.pushover", fake_pushover, raising=False)
    monkeypatch.setattr("manganotify.services.notifications.discord_notify", fake_discord, raising=False)
    return calls


@pytest.mark.asyncio
async def test_process_once_creates_notification(isolated_settings, fake_notifiers):
    save_watchlist(
        [
            {
                "id": 270,
                "title": "Naruto",
                "total_chapters": 699,
                "last_read": 698,
                "status": "reading",
                "notifications": {
                    "enabled": True,
                    "pushover": True,
                    "discord": True,
                    "only_when_reading": True,
                },
            }
        ]
    )

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(f"{isolated_settings.BASE}/v1/series/270/full").mock(
            return_value=Response(
                200,
                json={
                    "data": {
                        "id": 270,
                        "title": "NARUTO",
                        "total_chapters": "701",
                        "status": "releasing",
                        "last_updated_at": "2025-01-01T00:00:00Z",
                        "cover": {"small": "cover.jpg"},
                    }
                },
            )
        )

        async with httpx.AsyncClient() as client:
            app = SimpleNamespace(state=SimpleNamespace(client=client, poll_stats={}))
            result = await process_once(app)

    assert result == {"checked": 1}

    notifications = load_notifications()
    assert len(notifications) == 1
    note = notifications[0]
    assert note["series_id"] == 270
    assert note["new_total"] == 701
    assert note["notifications_enabled"] is True

    assert fake_notifiers["pushover"]
    assert fake_notifiers["discord"]

    watchlist = load_watchlist()
    assert watchlist[0]["total_chapters"] == 701
    assert watchlist[0]["status"] == "reading"
    assert watchlist[0]["last_checked"]


@pytest.mark.asyncio
async def test_process_once_respects_disabled_notifications(isolated_settings, fake_notifiers):
    save_watchlist(
        [
            {
                "id": 123,
                "title": "Test Series",
                "total_chapters": 10,
                "last_read": 10,
                "status": "reading",
                "notifications": {
                    "enabled": False,
                    "pushover": True,
                    "discord": True,
                    "only_when_reading": True,
                },
            }
        ]
    )

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(f"{isolated_settings.BASE}/v1/series/123/full").mock(
            return_value=Response(
                200,
                json={
                    "data": {
                        "id": 123,
                        "title": "Test Series",
                        "total_chapters": "11",
                        "status": "releasing",
                        "last_updated_at": "2025-01-01T00:00:00Z",
                    }
                },
            )
        )

        async with httpx.AsyncClient() as client:
            app = SimpleNamespace(state=SimpleNamespace(client=client, poll_stats={}))
            await process_once(app)

    assert fake_notifiers["pushover"] == []
    assert fake_notifiers["discord"] == []

    notifications = load_notifications()
    assert notifications[0]["notifications_enabled"] is False


@pytest.mark.asyncio
async def test_process_once_handles_http_errors(isolated_settings, fake_notifiers):
    save_watchlist(
        [
            {
                "id": 404,
                "title": "Broken",
                "total_chapters": 5,
                "last_read": 5,
                "status": "reading",
                "notifications": {"enabled": True},
            }
        ]
    )

    with respx.mock(assert_all_called=True) as respx_mock:
        respx_mock.get(f"{isolated_settings.BASE}/v1/series/404/full").mock(
            return_value=Response(404, json={"status": 404, "message": "Not Found"})
        )

        async with httpx.AsyncClient() as client:
            app = SimpleNamespace(state=SimpleNamespace(client=client, poll_stats={}))
            result = await process_once(app)

    assert result == {"checked": 1}
    assert load_notifications() == []
    assert fake_notifiers["pushover"] == []
    assert fake_notifiers["discord"] == []

    watchlist = load_watchlist()
    assert watchlist[0]["total_chapters"] == 5
