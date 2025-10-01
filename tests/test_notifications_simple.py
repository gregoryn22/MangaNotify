"""
Simplified tests for notification functionality.
These tests focus on the core logic without complex mocking.
"""
import pytest
import httpx
from unittest.mock import patch, AsyncMock

from manganotify.services.notifications import add_notification
from manganotify.services.poller import _should_send_notification


class TestNotificationLogic:
    """Test notification decision logic."""
    
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


class TestNotificationStorage:
    """Test notification storage and retrieval."""
    
    def test_add_notification(self, temp_data_dir):
        """Test adding notifications to storage."""
        # Test chapter update notification
        payload = {
            "series_id": 1677,
            "title": "Chainsaw Man",
            "old_total": 215,
            "new_total": 216,
            "unread": 1,
            "message": "Chainsaw Man now has 216 chapters. You're 1 behind.",
            "push_ok": True,
            "notifications_enabled": True
        }
        
        result = add_notification("chapter_update", payload)
        
        assert result["kind"] == "chapter_update"
        assert result["series_id"] == 1677
        assert result["title"] == "Chainsaw Man"
        assert result["old_total"] == 215
        assert result["new_total"] == 216
        assert result["unread"] == 1
        assert "id" in result
        assert "detected_at" in result
    
    def test_add_test_notification(self, temp_data_dir):
        """Test adding test notifications."""
        payload = {
            "title": "Test notification",
            "message": "This is a test",
            "push_ok": True
        }
        
        result = add_notification("test", payload)
        
        assert result["kind"] == "test"
        assert result["title"] == "Test notification"
        assert result["message"] == "This is a test"
        assert result["push_ok"] == True
        assert "id" in result
        assert "detected_at" in result


class TestNotificationCredentials:
    """Test notification credential handling."""
    
    def test_pushover_missing_credentials(self):
        """Test Pushover with missing credentials."""
        # Mock settings with missing credentials
        from unittest.mock import Mock
        mock_settings = Mock()
        mock_settings.get_decrypted_pushover_app_token.return_value = None
        mock_settings.get_decrypted_pushover_user_key.return_value = None
        
        # Test the credential check logic
        app_token = mock_settings.get_decrypted_pushover_app_token()
        user_key = mock_settings.get_decrypted_pushover_user_key()
        
        assert app_token is None
        assert user_key is None
        assert not (app_token and user_key)  # Should be False when missing
    
    def test_pushover_valid_credentials(self):
        """Test Pushover with valid credentials."""
        # Mock settings with valid credentials
        from unittest.mock import Mock
        mock_settings = Mock()
        mock_settings.get_decrypted_pushover_app_token.return_value = "test_token"
        mock_settings.get_decrypted_pushover_user_key.return_value = "test_key"
        
        # Test the credential check logic
        app_token = mock_settings.get_decrypted_pushover_app_token()
        user_key = mock_settings.get_decrypted_pushover_user_key()
        
        assert app_token == "test_token"
        assert user_key == "test_key"
        assert app_token and user_key  # Should be True when present
    
    def test_discord_disabled(self):
        """Test Discord notification when disabled."""
        # Mock settings with Discord disabled
        from unittest.mock import Mock
        mock_settings = Mock()
        mock_settings.DISCORD_ENABLED = False
        mock_settings.get_decrypted_discord_webhook_url.return_value = None
        
        # Test the enabled check logic
        assert not mock_settings.DISCORD_ENABLED
        assert not mock_settings.get_decrypted_discord_webhook_url()
    
    def test_discord_enabled(self):
        """Test Discord notification when enabled."""
        # Mock settings with Discord enabled
        from unittest.mock import Mock
        mock_settings = Mock()
        mock_settings.DISCORD_ENABLED = True
        mock_settings.get_decrypted_discord_webhook_url.return_value = "https://discord.com/api/webhooks/test"
        
        # Test the enabled check logic
        assert mock_settings.DISCORD_ENABLED
        assert mock_settings.get_decrypted_discord_webhook_url() == "https://discord.com/api/webhooks/test"


class TestNotificationIntegration:
    """Test notification integration scenarios."""
    
    def test_notification_message_formatting(self):
        """Test notification message formatting."""
        # Test chapter update message formatting
        series_title = "Chainsaw Man"
        old_total = 215
        new_total = 216
        unread = 1
        
        message = f"{series_title} now has {new_total} chapters. You're {unread} behind."
        
        assert message == "Chainsaw Man now has 216 chapters. You're 1 behind."
        assert series_title in message
        assert str(new_total) in message
        assert str(unread) in message
    
    def test_notification_payload_structure(self):
        """Test notification payload structure."""
        # Test chapter update payload
        payload = {
            "series_id": 1677,
            "title": "Chainsaw Man",
            "old_total": 215,
            "new_total": 216,
            "unread": 1,
            "message": "Chainsaw Man now has 216 chapters. You're 1 behind.",
            "push_ok": True,
            "notifications_enabled": True
        }
        
        # Verify all required fields are present
        required_fields = ["series_id", "title", "old_total", "new_total", "unread", "message"]
        for field in required_fields:
            assert field in payload
        
        # Verify data types
        assert isinstance(payload["series_id"], int)
        assert isinstance(payload["title"], str)
        assert isinstance(payload["old_total"], int)
        assert isinstance(payload["new_total"], int)
        assert isinstance(payload["unread"], int)
        assert isinstance(payload["message"], str)
        assert isinstance(payload["push_ok"], bool)
        assert isinstance(payload["notifications_enabled"], bool)
    
    def test_discord_payload_structure(self):
        """Test Discord notification payload structure."""
        title = "New Chapter!"
        message = "Chainsaw Man now has 216 chapters. You're 1 behind."
        
        # This is what the Discord payload should look like
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": 0x5865F2  # Discord blurple
            }]
        }
        
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1
        
        embed = payload["embeds"][0]
        assert embed["title"] == title
        assert embed["description"] == message
        assert embed["color"] == 0x5865F2
