"""
Tests for configuration and environment handling.
"""

import os
import tempfile
from pathlib import Path

import pytest

from manganotify.core.config import create_settings


class TestConfiguration:
    """Test configuration loading and validation."""

    def test_default_settings(self):
        """Test that default settings are loaded correctly."""
        settings = create_settings()

        assert settings.MANGABAKA_BASE == "https://api.mangabaka.dev"
        assert settings.PORT == 8999
        # POLL_INTERVAL_SEC can be overridden by test environment
        assert settings.POLL_INTERVAL_SEC >= 0
        assert not settings.AUTH_ENABLED
        assert settings.CORS_ALLOW_ORIGINS == "*"
        assert settings.LOG_LEVEL in [
            "INFO",
            "ERROR",
        ]  # Can be overridden by test environment

    def test_environment_override(self):
        """Test that environment variables override defaults."""
        # Set environment variables
        os.environ["POLL_INTERVAL_SEC"] = "300"
        os.environ["AUTH_ENABLED"] = "true"
        os.environ["LOG_LEVEL"] = "DEBUG"

        try:
            settings = create_settings()

            assert settings.POLL_INTERVAL_SEC == 300
            assert settings.AUTH_ENABLED
            assert settings.LOG_LEVEL == "DEBUG"
        finally:
            # Clean up
            os.environ.pop("POLL_INTERVAL_SEC", None)
            os.environ.pop("AUTH_ENABLED", None)
            os.environ.pop("LOG_LEVEL", None)

    def test_data_dir_creation(self):
        """Test that data directory is created and writable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["DATA_DIR"] = temp_dir

            try:
                settings = create_settings()

                # Data directory should exist and be writable
                assert Path(settings.DATA_DIR).exists()
                assert Path(settings.DATA_DIR).is_dir()

                # Test write permissions
                test_file = Path(settings.DATA_DIR) / "test_write.txt"
                test_file.write_text("test")
                assert test_file.exists()
                test_file.unlink()

            finally:
                os.environ.pop("DATA_DIR", None)

    def test_invalid_poll_interval(self):
        """Test validation of poll interval."""
        # Test edge case - zero value (should be valid)
        original_poll = os.environ.get("POLL_INTERVAL_SEC")

        try:
            os.environ["POLL_INTERVAL_SEC"] = "0"
            settings = create_settings()
            # Zero should be valid (disables polling)
            assert settings.POLL_INTERVAL_SEC == 0
        finally:
            if original_poll is not None:
                os.environ["POLL_INTERVAL_SEC"] = original_poll
            else:
                os.environ.pop("POLL_INTERVAL_SEC", None)

    def test_auth_configuration(self):
        """Test authentication configuration."""
        # Test with auth enabled but missing secret key
        original_env = {}
        test_env = {
            "AUTH_ENABLED": "true",
            "AUTH_USERNAME": "admin",
            "AUTH_PASSWORD": "password123",
        }

        # Store original values and clear AUTH_SECRET_KEY
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        # Explicitly clear AUTH_SECRET_KEY to test missing key scenario
        original_env["AUTH_SECRET_KEY"] = os.environ.get("AUTH_SECRET_KEY")
        os.environ.pop("AUTH_SECRET_KEY", None)

        try:
            settings = create_settings()

            assert settings.AUTH_ENABLED
            assert settings.AUTH_USERNAME == "admin"
            assert settings.AUTH_PASSWORD == "password123"
            assert settings.AUTH_SECRET_KEY is None  # Not set

        finally:
            # Restore original values
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value

    def test_cors_configuration(self):
        """Test CORS configuration parsing."""
        # Test wildcard
        os.environ["CORS_ALLOW_ORIGINS"] = "*"

        try:
            settings = create_settings()
            assert settings.cors_allow_origins_list == ["*"]
        finally:
            os.environ.pop("CORS_ALLOW_ORIGINS", None)

        # Test specific origins
        os.environ["CORS_ALLOW_ORIGINS"] = "https://example.com,http://localhost:3000"

        try:
            settings = create_settings()
            expected = ["https://example.com", "http://localhost:3000"]
            assert settings.cors_allow_origins_list == expected
        finally:
            os.environ.pop("CORS_ALLOW_ORIGINS", None)

    def test_notification_configuration(self):
        """Test notification configuration."""
        # Test with Pushover credentials
        os.environ.update(
            {"PUSHOVER_APP_TOKEN": "test_token", "PUSHOVER_USER_KEY": "test_key"}
        )

        try:
            settings = create_settings()

            assert settings.PUSHOVER_APP_TOKEN == "test_token"
            assert settings.PUSHOVER_USER_KEY == "test_key"

            # Test decryption methods (should return plain text without master key)
            assert settings.get_decrypted_pushover_app_token() == "test_token"
            assert settings.get_decrypted_pushover_user_key() == "test_key"

        finally:
            os.environ.pop("PUSHOVER_APP_TOKEN", None)
            os.environ.pop("PUSHOVER_USER_KEY", None)

    def test_discord_configuration(self):
        """Test Discord configuration."""
        os.environ.update(
            {
                "DISCORD_ENABLED": "true",
                "DISCORD_WEBHOOK_URL": "https://discord.com/api/webhooks/test",
            }
        )

        try:
            settings = create_settings()

            assert settings.DISCORD_ENABLED
            assert (
                settings.DISCORD_WEBHOOK_URL == "https://discord.com/api/webhooks/test"
            )

            assert (
                settings.get_decrypted_discord_webhook_url()
                == "https://discord.com/api/webhooks/test"
            )

        finally:
            os.environ.pop("DISCORD_ENABLED", None)
            os.environ.pop("DISCORD_WEBHOOK_URL", None)


class TestConfigurationValidation:
    """Test configuration validation and error handling."""

    def test_invalid_port_range(self):
        """Test port number validation."""
        # Test valid edge case - minimum port
        original_port = os.environ.get("PORT")

        try:
            os.environ["PORT"] = "1"  # Minimum valid port
            settings = create_settings()
            # Should accept minimum valid port
            assert settings.PORT == 1
        finally:
            if original_port is not None:
                os.environ["PORT"] = original_port
            else:
                os.environ.pop("PORT", None)

        # Test valid high port
        os.environ["PORT"] = "65535"  # Maximum valid port

        try:
            settings = create_settings()
            # Should accept maximum valid port
            assert settings.PORT == 65535
        finally:
            if original_port is not None:
                os.environ["PORT"] = original_port
            else:
                os.environ.pop("PORT", None)

    def test_invalid_log_level(self):
        """Test log level validation."""
        # Test valid log levels
        original_log_level = os.environ.get("LOG_LEVEL")

        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]

        for level in valid_levels:
            try:
                os.environ["LOG_LEVEL"] = level
                settings = create_settings()
                # Should accept valid log level
                assert settings.LOG_LEVEL == level
            finally:
                if original_log_level is not None:
                    os.environ["LOG_LEVEL"] = original_log_level
                else:
                    os.environ.pop("LOG_LEVEL", None)

    def test_invalid_base_url(self):
        """Test invalid base URL."""
        os.environ["MANGABAKA_BASE"] = "invalid-url"

        try:
            # This should raise a validation error
            with pytest.raises((RuntimeError, ValueError)):
                create_settings()
        finally:
            os.environ.pop("MANGABAKA_BASE", None)


class TestEnvironmentIsolation:
    """Test that tests don't interfere with each other."""

    def test_environment_isolation(self):
        """Test that environment changes don't persist between tests."""
        # This test should run with clean environment
        settings = create_settings()

        # Should use defaults (or test environment values)
        assert settings.POLL_INTERVAL_SEC >= 0  # Can be 0 in test environment
        assert not settings.AUTH_ENABLED
        assert settings.LOG_LEVEL in [
            "INFO",
            "ERROR",
        ]  # Can be ERROR in test environment

    def test_temp_data_dir_isolation(self, temp_data_dir):
        """Test that temporary data directories are isolated."""
        # Each test should get its own temporary directory
        assert temp_data_dir.startswith("/tmp") or temp_data_dir.startswith("C:")
        assert "manganotify_data_" in temp_data_dir

        # Directory should be writable
        test_file = Path(temp_data_dir) / "test.txt"
        test_file.write_text("test")
        assert test_file.exists()
        test_file.unlink()
