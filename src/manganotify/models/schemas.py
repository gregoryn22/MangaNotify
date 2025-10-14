from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

StatusLiteral = Literal["reading", "to-read", "on-hold", "finished", "dropped"]


class NotificationPreferences(BaseModel):
    """Per-series notification preferences"""

    enabled: bool = Field(
        default=True, description="Enable notifications for this series"
    )
    pushover: bool = Field(default=True, description="Send Pushover notifications")
    discord: bool = Field(default=True, description="Send Discord notifications")
    only_when_reading: bool = Field(
        default=True, description="Only notify when status is 'reading'"
    )


class WatchlistAdd(BaseModel):
    id: int = Field(..., description="Series ID")
    title: str | None = None
    total_chapters: int | None = None
    last_read: int | None = None
    status: StatusLiteral | None = Field(default=None)
    notifications: NotificationPreferences | None = Field(
        default_factory=NotificationPreferences
    )


class ProgressPatch(BaseModel):
    mark_latest: bool | None = None
    last_read: int | None = None
    decrement: int | None = None


class StatusPatch(BaseModel):
    status: StatusLiteral


class NotificationPreferencesPatch(BaseModel):
    """Patch model for updating notification preferences"""

    enabled: bool | None = None
    pushover: bool | None = None
    discord: bool | None = None
    only_when_reading: bool | None = None
