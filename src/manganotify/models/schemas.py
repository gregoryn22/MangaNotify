from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal


StatusLiteral = Literal["reading", "releasing", "to-read", "on-hold", "finished", "dropped"]


class NotificationPreferences(BaseModel):
    """Per-series notification preferences"""
    enabled: bool = Field(default=True, description="Enable notifications for this series")
    pushover: bool = Field(default=True, description="Send Pushover notifications")
    discord: bool = Field(default=True, description="Send Discord notifications")
    only_when_reading: bool = Field(default=True, description="Only notify when status is 'reading'")


class WatchlistAdd(BaseModel):
    id: int = Field(..., description="Series ID")
    title: Optional[str] = None
    total_chapters: Optional[int] = None
    last_read: Optional[int] = None
    status: Optional[StatusLiteral] = Field(default=None)
    notifications: Optional[NotificationPreferences] = Field(default_factory=NotificationPreferences)


class ProgressPatch(BaseModel):
    mark_latest: Optional[bool] = None
    last_read: Optional[int] = None
    decrement: Optional[int] = None


class StatusPatch(BaseModel):
    status: StatusLiteral


class NotificationPreferencesPatch(BaseModel):
    """Patch model for updating notification preferences"""
    enabled: Optional[bool] = None
    pushover: Optional[bool] = None
    discord: Optional[bool] = None
    only_when_reading: Optional[bool] = None

