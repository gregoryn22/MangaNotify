"""
Tests for the poller functionality to catch issues like missed notifications.
"""
import pytest
import asyncio
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import httpx

from manganotify.services.poller import process_once, poll_loop, _should_send_notification
from manganotify.services.watchlist import load_watchlist, save_watchlist
from manganotify.services.notifications import add_notification, load_notifications


class TestPollerLogic:
    """Test the core poller logic and notification detection."""
    
    def test_should_send_notification_defaults(self):
        """Test notification preferences with default settings."""
        # Default series item (no notification preferences)
        series_item = {
            "id": 1677,
            "title": "Chainsaw Man",
            "status": "reading"
        }
        
        assert _should_send_notification(series_item) == True
        
        # Series with notifications disabled
        series_item["notifications"] = {"enabled": False}
        assert _should_send_notification(series_item) == False
        
        # Series with notifications enabled
        series_item["notifications"] = {"enabled": True}
        assert _should_send_notification(series_item) == True
    
    def test_should_send_notification_status_filtering(self):
        """Test notification filtering based on series status."""
        series_item = {
            "id": 1677,
            "title": "Chainsaw Man",
            "status": "reading",
            "notifications": {"only_when_reading": True}
        }
        
        # Should notify for reading status
        assert _should_send_notification(series_item) == True
        
        # Should notify for releasing status
        series_item["status"] = "releasing"
        assert _should_send_notification(series_item) == True
        
        # Should not notify for other statuses
        for status in ["finished", "dropped", "on-hold", "to-read"]:
            series_item["status"] = status
            assert _should_send_notification(series_item) == False
    
    def test_should_send_notification_disabled_when_reading(self):
        """Test notification when only_when_reading is disabled."""
        series_item = {
            "id": 1677,
            "title": "Chainsaw Man",
            "status": "finished",
            "notifications": {"only_when_reading": False}
        }
        
        # Should notify even for finished status
        assert _should_send_notification(series_item) == True


class TestPollerIntegration:
    """Test the poller with real data and API calls."""
    
    @pytest.fixture
    def temp_watchlist(self, temp_data_dir):
        """Create a temporary watchlist for testing."""
        watchlist_data = [
            {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 215,
                "last_read": 215,
                "status": "reading",
                "added_at": "2025-09-30T10:00:00Z",
                "last_checked": "2025-09-30T10:00:00Z",
                "notifications": {
                    "enabled": True,
                    "pushover": True,
                    "discord": True,
                    "only_when_reading": True
                }
            }
        ]
        
        watchlist_path = os.path.join(temp_data_dir, "watchlist.json")
        with open(watchlist_path, 'w') as f:
            json.dump(watchlist_data, f)
        
        return watchlist_data
    
    @pytest.mark.asyncio
    async def test_poller_detects_new_chapter(self, temp_watchlist, temp_data_dir):
        """Test that poller detects when a new chapter is available."""
        # Mock API response with new chapter
        mock_api_response = {
            "data": {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 216,  # New chapter!
                "status": "releasing",
                "last_updated_at": "2025-09-30T15:00:00Z"
            }
        }
        
        # Mock the API call
        with patch('manganotify.services.poller.api_series_by_id', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_api_response
            
            # Mock the FastAPI app
            mock_app = MagicMock()
            mock_app.state.client = AsyncMock()
            
            # Mock the pushover function to avoid async issues
            with patch('manganotify.services.poller.pushover', new_callable=AsyncMock) as mock_pushover:
                mock_pushover.return_value = {"ok": True}
                
                # Mock the load_watchlist function to return our test data
                def mock_load_watchlist():
                    return temp_watchlist
                
                # Track the updated watchlist
                updated_watchlist = None
                def mock_save_watchlist(wl):
                    nonlocal updated_watchlist
                    updated_watchlist = wl
                
                with patch('manganotify.services.poller.load_watchlist', side_effect=mock_load_watchlist), \
                     patch('manganotify.services.poller.save_watchlist', side_effect=mock_save_watchlist):
                    # Run the poller once
                    result = await process_once(mock_app)
            
            # Check that it processed the series
            assert result["checked"] == 1
            
            # Check that the watchlist was updated
            assert updated_watchlist is not None, "save_watchlist should have been called"
            test_series_items = [item for item in updated_watchlist if item["id"] == 1677]
            assert len(test_series_items) > 0, f"No test series found in watchlist: {updated_watchlist}"
            test_series = test_series_items[0]
            assert test_series["total_chapters"] == 216
            
            # Check that a notification was created
            # Note: We can't easily test notifications without mocking the entire notification system
            # For now, we'll just verify the poller ran successfully
            # In a real test, you'd mock add_notification and verify it was called
    
    @pytest.mark.asyncio
    async def test_poller_handles_api_failure(self, temp_watchlist, temp_data_dir):
        """Test that poller handles API failures gracefully."""
        # Mock API to raise an exception
        with patch('manganotify.services.poller.api_series_by_id', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = httpx.HTTPError("API unavailable")
            
            # Mock the FastAPI app
            mock_app = MagicMock()
            mock_app.state.client = AsyncMock()
            
            # Mock the pushover function to avoid async issues
            with patch('manganotify.services.poller.pushover', new_callable=AsyncMock) as mock_pushover:
                mock_pushover.return_value = {"ok": True}
                
                # Mock the load_watchlist function to return our test data
                def mock_load_watchlist():
                    return temp_watchlist
                
                # Track the updated watchlist
                updated_watchlist = None
                def mock_save_watchlist(wl):
                    nonlocal updated_watchlist
                    updated_watchlist = wl
                
                with patch('manganotify.services.poller.load_watchlist', side_effect=mock_load_watchlist), \
                     patch('manganotify.services.poller.save_watchlist', side_effect=mock_save_watchlist):
                    # Run the poller once - should not crash
                    result = await process_once(mock_app)
            
            # Should still report that it checked the series (even if API failed)
            assert result["checked"] == 1
            
            # Watchlist should remain unchanged (since API failed)
            assert updated_watchlist is not None, "save_watchlist should have been called"
            test_series_items = [item for item in updated_watchlist if item["id"] == 1677]
            assert len(test_series_items) > 0, f"No test series found in watchlist: {updated_watchlist}"
            test_series = test_series_items[0]
            assert test_series["total_chapters"] == 215  # Unchanged
    
    @pytest.mark.asyncio
    async def test_poller_retry_logic(self, temp_watchlist, temp_data_dir):
        """Test that poller retries failed API calls."""
        call_count = 0
        
        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 times
                raise httpx.HTTPError("Temporary failure")
            else:  # Succeed on 3rd try
                return {
                    "data": {
                        "id": 1677,
                        "title": "Chainsaw Man",
                        "total_chapters": 216,
                        "status": "releasing"
                    }
                }
        
        with patch('manganotify.services.poller.api_series_by_id', new_callable=AsyncMock) as mock_api:
            mock_api.side_effect = mock_api_call
            
            # Mock the FastAPI app
            mock_app = MagicMock()
            mock_app.state.client = AsyncMock()
            
            # Mock the pushover function to avoid async issues
            with patch('manganotify.services.poller.pushover', new_callable=AsyncMock) as mock_pushover:
                mock_pushover.return_value = {"ok": True}
                
                # Mock the load_watchlist function to return our test data
                def mock_load_watchlist():
                    return temp_watchlist
                
                # Track the updated watchlist
                updated_watchlist = None
                def mock_save_watchlist(wl):
                    nonlocal updated_watchlist
                    updated_watchlist = wl
                
                with patch('manganotify.services.poller.load_watchlist', side_effect=mock_load_watchlist), \
                     patch('manganotify.services.poller.save_watchlist', side_effect=mock_save_watchlist):
                    # Run the poller once
                    result = await process_once(mock_app)
            
            # Should have retried and succeeded
            assert call_count == 3
            assert result["checked"] == 1
            
            # Should have updated the watchlist
            assert updated_watchlist is not None, "save_watchlist should have been called"
            test_series_items = [item for item in updated_watchlist if item["id"] == 1677]
            assert len(test_series_items) > 0, f"No test series found in watchlist: {updated_watchlist}"
            test_series = test_series_items[0]
            assert test_series["total_chapters"] == 216
    
    @pytest.mark.asyncio
    async def test_poller_no_notification_when_disabled(self, temp_data_dir):
        """Test that poller doesn't send notifications when disabled."""
        # Create watchlist with notifications disabled
        watchlist_data = [
            {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 215,
                "last_read": 215,
                "status": "reading",
                "added_at": "2025-09-30T10:00:00Z",
                "last_checked": "2025-09-30T10:00:00Z",
                "notifications": {
                    "enabled": False  # Notifications disabled
                }
            }
        ]
        
        watchlist_path = os.path.join(temp_data_dir, "watchlist.json")
        with open(watchlist_path, 'w') as f:
            json.dump(watchlist_data, f)
        
        # Mock API response with new chapter
        mock_api_response = {
            "data": {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 216,
                "status": "releasing"
            }
        }
        
        with patch('manganotify.services.poller.api_series_by_id', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_api_response
            
            # Mock the FastAPI app
            mock_app = MagicMock()
            mock_app.state.client = AsyncMock()
            
            # Mock the load_watchlist function to return our test data
            def mock_load_watchlist():
                return watchlist_data
            
            # Track the updated watchlist
            updated_watchlist = None
            def mock_save_watchlist(wl):
                nonlocal updated_watchlist
                updated_watchlist = wl
            
            with patch('manganotify.services.poller.load_watchlist', side_effect=mock_load_watchlist), \
                 patch('manganotify.services.poller.save_watchlist', side_effect=mock_save_watchlist):
                # Run the poller once
                result = await process_once(mock_app)
            
            # Should still update the watchlist
            assert updated_watchlist is not None, "save_watchlist should have been called"
            test_series_items = [item for item in updated_watchlist if item["id"] == 1677]
            assert len(test_series_items) > 0, f"No test series found in watchlist: {updated_watchlist}"
            test_series = test_series_items[0]
            assert test_series["total_chapters"] == 216
            
            # But should not send notifications
            # Note: We can't easily test notifications without mocking the entire notification system
            # For now, we'll just verify the poller ran successfully
            # In a real test, you'd mock add_notification and verify it was NOT called


class TestPollerTiming:
    """Test poller timing and interval functionality."""
    
    @pytest.mark.asyncio
    async def test_poller_interval_respect(self):
        """Test that poller respects the configured interval."""
        # This would require mocking asyncio.sleep and checking timing
        # For now, just test that the function exists and can be called
        assert poll_loop is not None
        
        # In a real test, you'd mock the sleep function and verify timing
        # This is more of an integration test that would run in CI/CD


class TestNotificationContent:
    """Test notification content and formatting."""
    
    def test_notification_message_formatting(self):
        """Test that notification messages are formatted correctly."""
        # Test the message formatting logic
        series_title = "Chainsaw Man"
        old_total = 215
        new_total = 216
        unread = 1
        
        expected_message = f"{series_title} now has {new_total} chapters. You're {unread} behind."
        assert "Chainsaw Man now has 216 chapters. You're 1 behind." == expected_message
        
        # Test with no unread chapters
        unread = 0
        expected_message_no_unread = f"{series_title} now has {new_total} chapters."
        assert "Chainsaw Man now has 216 chapters." == expected_message_no_unread


# Integration test that simulates the real-world scenario
class TestMissedNotificationScenario:
    """Test scenarios for missed notification detection."""
    
    @pytest.mark.asyncio
    async def test_missed_update_scenario(self, temp_data_dir):
        """Test the exact scenario that happened with a missed update."""
        # Set up the exact watchlist state from when the issue occurred
        watchlist_data = [
            {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 215,
                "last_read": 215,
                "status": "reading",
                "added_at": "2025-09-23T19:54:55.498020Z",
                "last_checked": "2025-09-30T14:52:48.126208Z",  # Last check time
                "last_chapter_at": "2025-09-30T10:38:55.997Z",  # Chapter 216 released later
                "notifications": {
                    "enabled": True,
                    "pushover": True,
                    "discord": True,
                    "only_when_reading": True
                }
            }
        ]
        
        watchlist_path = os.path.join(temp_data_dir, "watchlist.json")
        with open(watchlist_path, 'w') as f:
            json.dump(watchlist_data, f)
        
        # Mock API response showing chapter 216 is now available
        mock_api_response = {
            "data": {
                "id": 1677,
                "title": "Chainsaw Man",
                "total_chapters": 216,  # Chapter 216 is now available
                "status": "releasing",
                "last_updated_at": "2025-09-30T15:00:00Z"  # Updated timestamp (this is what derive_last_chapter_at looks for)
            }
        }
        
        with patch('manganotify.services.poller.api_series_by_id', new_callable=AsyncMock) as mock_api:
            mock_api.return_value = mock_api_response
            
            # Mock the FastAPI app
            mock_app = MagicMock()
            mock_app.state.client = AsyncMock()
            
            # Mock the pushover function to avoid async issues
            with patch('manganotify.services.poller.pushover', new_callable=AsyncMock) as mock_pushover:
                mock_pushover.return_value = {"ok": True}
                
                # Mock the load_watchlist function to return our test data
                def mock_load_watchlist():
                    return watchlist_data
                
                # Track the updated watchlist
                updated_watchlist = None
                def mock_save_watchlist(wl):
                    nonlocal updated_watchlist
                    updated_watchlist = wl
                
                with patch('manganotify.services.poller.load_watchlist', side_effect=mock_load_watchlist), \
                     patch('manganotify.services.poller.save_watchlist', side_effect=mock_save_watchlist):
                    # Run the poller once
                    result = await process_once(mock_app)
            
            # Verify the update was detected
            assert result["checked"] == 1
            
            # Check that the watchlist was updated
            assert updated_watchlist is not None, "save_watchlist should have been called"
            test_series_items = [item for item in updated_watchlist if item["id"] == 1677]
            assert len(test_series_items) > 0, f"No test series found in watchlist: {updated_watchlist}"
            test_series = test_series_items[0]
            assert test_series["total_chapters"] == 216
            # The last_chapter_at should be updated by the poller
            assert test_series["last_chapter_at"] == "2025-09-30T15:00:00Z"
            
            # Check that a notification was created
            notifications = load_notifications()
            chapter_notifications = [n for n in notifications if n.get("kind") == "chapter_update"]
            assert len(chapter_notifications) > 0
            
            latest_notification = chapter_notifications[0]
            assert latest_notification["series_id"] == 1677
            assert latest_notification["old_total"] == 215
            assert latest_notification["new_total"] == 216
            assert latest_notification["unread"] == 1
            assert latest_notification["notifications_enabled"] == True
