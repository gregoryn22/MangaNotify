# src/manganotify/core/config.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App / API
    MANGABAKA_BASE: str = Field(
        default="https://api.mangabaka.dev", alias="MANGABAKA_BASE"
    )

    # Storage
    DATA_DIR: Path = Field(default=Path("./data"), alias="DATA_DIR")

    # Pushover
    PUSHOVER_USER_KEY: Optional[str] = Field(default=None, alias="PUSHOVER_USER_KEY")
    PUSHOVER_APP_TOKEN: Optional[str] = Field(default=None, alias="PUSHOVER_APP_TOKEN")

    # Polling / server
    POLL_INTERVAL_SEC: int = Field(default=1800, alias="POLL_INTERVAL_SEC")
    PORT: int = Field(default=8999, alias="PORT")

    # Read .env automatically (you can keep python-dotenv out of your code)
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    # Back-compat helpers if your code expects old names
    @property
    def BASE(self) -> str:
        return self.MANGABAKA_BASE.rstrip("/")


settings = Settings()

# Convenience paths (optional; do this where you set up storage)
DATA_DIR = settings.DATA_DIR
WATCHLIST_PATH = DATA_DIR / "watchlist.json"
NOTIFY_PATH = DATA_DIR / "notifications.json"
