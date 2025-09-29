# src/manganotify/core/config.py
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Compute a package-relative default: <repo>/src/manganotify/data
PKG_ROOT = Path(__file__).resolve().parents[1]      # .../src/manganotify
PKG_DATA = (PKG_ROOT / "data").resolve()

class Settings(BaseSettings):
    # Upstream API base
    MANGABAKA_BASE: str = Field(default="https://api.mangabaka.dev", pattern=r"^https?://[a-zA-Z0-9.-]+")

    # Storage: prefer env, else package-relative default
    DATA_DIR: Path = Field(default=PKG_DATA)

    # Push + polling
    # It is recommended to set all secrets (including Pushover and Discord) in a .env file, not in code.
    PUSHOVER_USER_KEY: Optional[str] = Field(default=None, description="Pushover user key")
    PUSHOVER_APP_TOKEN: Optional[str] = Field(default=None, description="Pushover app token")
    DISCORD_WEBHOOK_URL: Optional[str] = Field(default=None, description="Discord webhook URL")
    DISCORD_ENABLED: bool = Field(default=False, description="Enable Discord notifications")
    POLL_INTERVAL_SEC: int = 1800
    PORT: int = 8999

    # CORS
    # Comma-separated list or '*' for all. Example: "https://example.com, http://localhost:5173"
    # WARNING: "*" allows any origin - only use in development!
    CORS_ALLOW_ORIGINS: str = Field(default="*")

    # Logging
    LOG_LEVEL: str = Field(default="INFO")  # DEBUG|INFO|WARNING|ERROR
    LOG_FORMAT: str = Field(default="plain")  # plain|json

    # Auth (optional)
    AUTH_ENABLED: bool = Field(default=False, description="Enable authentication")
    AUTH_SECRET_KEY: Optional[str] = Field(default=None, description="JWT secret key (required if auth enabled)")
    AUTH_USERNAME: str = Field(default="admin", description="Login username")
    AUTH_PASSWORD: str = Field(default="", description="Login password (required if auth enabled)")
    AUTH_TOKEN_EXPIRE_HOURS: int = Field(default=24, description="JWT token expiration in hours")

    # Encryption
    MASTER_KEY: Optional[str] = Field(default=None, description="Master key for credential encryption")

    # System/Environment variables (optional)
    TZ: Optional[str] = Field(default=None, description="Timezone")
    PYTHONDONTWRITEBYTECODE: Optional[str] = Field(default=None, description="Python bytecode setting")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    @property
    def BASE(self) -> str:
        return self.MANGABAKA_BASE.rstrip("/")

    @property
    def cors_allow_origins_list(self) -> list[str]:
        raw = (self.CORS_ALLOW_ORIGINS or "").strip()
        if raw == "*" or raw == "":
            return ["*"]
        return [s.strip() for s in raw.split(",") if s.strip()]
    
    def get_decrypted_pushover_app_token(self) -> Optional[str]:
        """Get decrypted Pushover app token."""
        if not self.PUSHOVER_APP_TOKEN or not self.MASTER_KEY:
            return self.PUSHOVER_APP_TOKEN
        
        from .crypto import decrypt_credential
        return decrypt_credential(self.PUSHOVER_APP_TOKEN, self.MASTER_KEY)
    
    def get_decrypted_pushover_user_key(self) -> Optional[str]:
        """Get decrypted Pushover user key."""
        if not self.PUSHOVER_USER_KEY or not self.MASTER_KEY:
            return self.PUSHOVER_USER_KEY
        
        from .crypto import decrypt_credential
        return decrypt_credential(self.PUSHOVER_USER_KEY, self.MASTER_KEY)
    
    def get_decrypted_discord_webhook_url(self) -> Optional[str]:
        """Get decrypted Discord webhook URL."""
        if not self.DISCORD_WEBHOOK_URL or not self.MASTER_KEY:
            return self.DISCORD_WEBHOOK_URL
        
        from .crypto import decrypt_credential
        return decrypt_credential(self.DISCORD_WEBHOOK_URL, self.MASTER_KEY)

settings = Settings()

# Ensure the directory exists and is writable
def _ensure_data_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    test = p / ".write_test"
    try:
        test.write_text("ok", encoding="utf-8")
        test.unlink(missing_ok=True)
    except Exception as e:
        raise RuntimeError(f"DATA_DIR not writable: {p} ({e})")
    return p

DATA_DIR = _ensure_data_dir(settings.DATA_DIR)
WATCHLIST_PATH = DATA_DIR / "watchlist.json"
NOTIFY_PATH   = DATA_DIR / "notifications.json"
