"""
Tests for API endpoints to ensure they work correctly.
"""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestWatchlistEndpoints:
    """Test watchlist-related API endpoints."""

    @pytest.fixture
    def client(self, patched_app):
        """Create a test client."""
        return TestClient(patched_app)

    @pytest.fixture
    def sample_watchlist(self, temp_data_dir):
        """Create a sample watchlist for testing."""
        watchlist_data = [
            {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 216,
                "last_read": 215,
                "status": "reading",
                "added_at": "2025-09-30T10:00:00Z",
                "last_checked": "2025-09-30T15:00:00Z",
                "notifications": {
                    "enabled": True,
                    "pushover": True,
                    "discord": True,
                    "only_when_reading": True,
                },
            },
            {
                "id": 377,
                "title": "One Piece",
                "total_chapters": 1161,
                "last_read": 1160,
                "status": "reading",
                "added_at": "2025-09-30T10:00:00Z",
                "last_checked": "2025-09-30T15:00:00Z",
                "notifications": {
                    "enabled": True,
                    "pushover": True,
                    "discord": True,
                    "only_when_reading": True,
                },
            },
        ]

        watchlist_path = os.path.join(temp_data_dir, "watchlist.json")
        with open(watchlist_path, "w") as f:
            json.dump(watchlist_data, f)

        return watchlist_data

    def test_get_watchlist(self, client, sample_watchlist):
        """Test getting the watchlist."""
        response = client.get("/api/watchlist")
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2

        # Check that unread counts are calculated correctly
        chainsaw_man = next(item for item in data["data"] if item["id"] == 1677)
        assert chainsaw_man["unread"] == 1  # 216 - 215
        assert chainsaw_man["is_behind"]

        one_piece = next(item for item in data["data"] if item["id"] == 377)
        assert one_piece["unread"] == 1  # 1161 - 1160
        assert one_piece["is_behind"]

    def test_get_watchlist_with_status_filter(self, client, sample_watchlist):
        """Test getting watchlist with status filter."""
        response = client.get("/api/watchlist?status=reading")
        assert response.status_code == 200

        data = response.json()
        assert len(data["data"]) == 2  # Both series are "reading"

        # Test with different status
        response = client.get("/api/watchlist?status=finished")
        assert response.status_code == 200

        data = response.json()
        assert len(data["data"]) == 0  # No finished series

    def test_watchlist_import_endpoint(self, client, temp_data_dir):
        """Test the watchlist import endpoint."""
        # Create import data
        import_data = [
            {
                "id": 123,
                "title": "Test Manga",
                "total_chapters": 10,
                "last_read": 5,
                "status": "reading",
                "authors": ["Test Author"],
                "artists": ["Test Artist"],
            },
            {
                "id": 456,
                "title": "Another Test Manga",
                "total_chapters": 20,
                "last_read": 20,
                "status": "finished",
            },
        ]

        # Import the data
        response = client.post("/api/watchlist/import", json=import_data)
        assert response.status_code == 200

        result = response.json()
        assert result["ok"]
        assert result["imported"] == 2
        assert result["skipped"] == 0

        # Verify the data was imported
        response = client.get("/api/watchlist")
        assert response.status_code == 200

        data = response.json()
        assert len(data["data"]) == 2

        # Check imported data
        test_manga = next(item for item in data["data"] if item["id"] == 123)
        assert test_manga["title"] == "Test Manga"
        assert test_manga["total_chapters"] == 10
        assert test_manga["last_read"] == 5
        assert test_manga["status"] == "reading"
        assert test_manga["authors"] == ["Test Author"]
        assert test_manga["artists"] == ["Test Artist"]

        another_manga = next(item for item in data["data"] if item["id"] == 456)
        assert another_manga["title"] == "Another Test Manga"
        assert another_manga["status"] == "finished"

    def test_watchlist_import_duplicates(self, client, sample_watchlist):
        """Test importing duplicate items."""
        # Try to import the same series again (already exists)
        import_data = [
            {
                "id": 1677,  # Already exists
                "title": "Chainsaw Man",
                "total_chapters": 216,
                "last_read": 215,
                "status": "reading",
            },
            {
                "id": 999,  # New item
                "title": "New Manga",
                "total_chapters": 5,
                "last_read": 0,
                "status": "to-read",
            },
        ]

        response = client.post("/api/watchlist/import", json=import_data)
        assert response.status_code == 200

        result = response.json()
        assert result["imported"] == 1  # Only the new item
        assert result["skipped"] == 1  # Test series was skipped

        # Verify only the new item was added
        response = client.get("/api/watchlist")
        data = response.json()
        assert len(data["data"]) == 3  # Original 2 + 1 new

        new_manga = next(item for item in data["data"] if item["id"] == 999)
        assert new_manga["title"] == "New Manga"

    def test_watchlist_import_invalid_data(self, client):
        """Test importing invalid data."""
        # Test with non-array data
        response = client.post("/api/watchlist/import", json={"invalid": "data"})
        assert response.status_code == 400

        # Test with invalid JSON
        response = client.post("/api/watchlist/import", data="invalid json")
        assert response.status_code == 400

    def test_watchlist_import_missing_fields(self, client):
        """Test importing data with missing required fields."""
        import_data = [
            {
                # Missing id field
                "title": "Test Manga",
                "total_chapters": 10,
            },
            {"id": 123, "title": "Valid Manga", "total_chapters": 5},
        ]

        response = client.post("/api/watchlist/import", json=import_data)
        assert response.status_code == 200

        result = response.json()
        assert result["imported"] == 1  # Only the valid item
        assert result["skipped"] == 0

    def test_set_progress(self, client, sample_watchlist):
        """Test setting reading progress."""
        # Test incrementing progress
        response = client.patch("/api/watchlist/1677/progress", json={"last_read": 216})
        assert response.status_code == 200

        result = response.json()
        assert result["ok"]
        assert result["last_read"] == 216

        # Test marking as latest
        response = client.patch(
            "/api/watchlist/1677/progress", json={"mark_latest": True}
        )
        assert response.status_code == 200

        result = response.json()
        assert result["ok"]
        assert result["last_read"] == 216  # Should be total chapters

        # Test decrementing
        response = client.patch("/api/watchlist/1677/progress", json={"decrement": 1})
        assert response.status_code == 200

        result = response.json()
        assert result["ok"]
        assert result["last_read"] == 215

    def test_set_status(self, client, sample_watchlist):
        """Test setting series status."""
        response = client.patch(
            "/api/watchlist/1677/status", json={"status": "finished"}
        )
        assert response.status_code == 200

        result = response.json()
        assert result["ok"]
        assert result["status"] == "finished"

        # Verify the change
        response = client.get("/api/watchlist")
        data = response.json()
        chainsaw_man = next(item for item in data["data"] if item["id"] == 1677)
        assert chainsaw_man["status"] == "finished"

    def test_remove_from_watchlist(self, client, sample_watchlist):
        """Test removing items from watchlist."""
        response = client.delete("/api/watchlist/1677")
        assert response.status_code == 200

        result = response.json()
        assert result["removed"] == 1

        # Verify the item was removed
        response = client.get("/api/watchlist")
        data = response.json()
        assert len(data["data"]) == 1

        # Try to remove non-existent item
        response = client.delete("/api/watchlist/99999")
        assert response.status_code == 200

        result = response.json()
        assert result["removed"] == 0


class TestNotificationEndpoints:
    """Test notification-related endpoints."""

    @pytest.fixture
    def client(self, patched_app):
        """Create a test client."""
        return TestClient(patched_app)

    @pytest.fixture
    def sample_notifications(self, temp_data_dir):
        """Create sample notifications for testing."""
        notifications_data = [
            {
                "id": 1,
                "kind": "chapter_update",
                "detected_at": "2025-09-30T15:00:00Z",
                "series_id": 1677,
                "title": "Chainsaw Man",
                "old_total": 215,
                "new_total": 216,
                "unread": 1,
                "message": "Chainsaw Man now has 216 chapters. You're 1 behind.",
                "push_ok": True,
                "notifications_enabled": True,
            },
            {
                "id": 2,
                "kind": "test",
                "detected_at": "2025-09-30T15:01:00Z",
                "title": "Test notification",
                "message": "This is a test",
                "push_ok": True,
            },
        ]

        notifications_path = os.path.join(temp_data_dir, "notifications.json")
        with open(notifications_path, "w") as f:
            json.dump(notifications_data, f)

        return notifications_data

    def test_get_notifications(self, client, sample_notifications):
        """Test getting notifications."""
        response = client.get("/api/notifications")
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 2

        # Check notification content
        chapter_notification = next(
            n for n in data["data"] if n["kind"] == "chapter_update"
        )
        assert chapter_notification["series_id"] == 1677
        assert chapter_notification["title"] == "Chainsaw Man"
        assert chapter_notification["old_total"] == 215
        assert chapter_notification["new_total"] == 216

    def test_delete_notification(self, client, sample_notifications):
        """Test deleting individual notifications."""
        response = client.delete("/api/notifications/1")
        assert response.status_code == 200

        result = response.json()
        assert result["removed"] == 1

        # Verify the notification was removed
        response = client.get("/api/notifications")
        data = response.json()
        assert len(data["data"]) == 1

        # Try to delete non-existent notification
        response = client.delete("/api/notifications/999")
        assert response.status_code == 200

        result = response.json()
        assert result["removed"] == 0

    def test_clear_notifications(self, client, sample_notifications):
        """Test clearing all notifications."""
        response = client.delete("/api/notifications")
        assert response.status_code == 200

        result = response.json()
        assert result["removed"] == "all"

        # Verify all notifications were cleared
        response = client.get("/api/notifications")
        data = response.json()
        assert len(data["data"]) == 0


class TestHealthEndpoints:
    """Test health and status endpoints."""

    @pytest.fixture
    def client(self, patched_app):
        """Create a test client."""
        return TestClient(patched_app)

    def test_health_endpoint(self, client):
        """Test basic health endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["ok"]

    def test_health_details_endpoint(self, client):
        """Test detailed health endpoint."""
        response = client.get("/api/health/details")
        assert response.status_code == 200

        data = response.json()
        assert data["ok"]
        assert "poll" in data
        assert "interval_sec" in data
        assert data["interval_sec"] == 0  # Polling disabled in tests


class TestRefreshEndpoint:
    """Test the manual refresh endpoint."""

    @pytest.fixture
    def client(self, patched_app):
        """Create a test client."""
        return TestClient(patched_app)

    @pytest.mark.asyncio
    async def test_manual_refresh(self, client, temp_data_dir):
        """Test manual watchlist refresh."""
        # Create a watchlist with old data
        watchlist_data = [
            {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 215,
                "last_read": 215,
                "status": "reading",
                "added_at": "2025-09-30T10:00:00Z",
                "last_checked": "2025-09-30T10:00:00Z",
            }
        ]

        watchlist_path = os.path.join(temp_data_dir, "watchlist.json")
        with open(watchlist_path, "w") as f:
            json.dump(watchlist_data, f)

        # Mock API response with updated data
        mock_api_response = {
            "data": {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 216,  # Updated
                "status": "releasing",
                "last_chapter_at": "2025-09-30T15:00:00Z",
            }
        }

        with patch(
            "manganotify.services.poller.api_series_by_id", new_callable=AsyncMock
        ) as mock_api:
            mock_api.return_value = mock_api_response

            # Trigger manual refresh
            response = client.post("/api/watchlist/refresh")
            assert response.status_code == 200

            result = response.json()
            assert result["checked"] == 1

            # Verify the watchlist was updated
            response = client.get("/api/watchlist")
            data = response.json()
            chainsaw_man = next(item for item in data["data"] if item["id"] == 1677)
            assert chainsaw_man["total_chapters"] == 216
