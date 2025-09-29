from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal


StatusLiteral = Literal["reading", "to-read", "on-hold", "finished", "dropped"]


class WatchlistAdd(BaseModel):
    id: int = Field(..., description="Series ID")
    title: Optional[str] = None
    total_chapters: Optional[int] = None
    last_read: Optional[int] = None
    status: Optional[StatusLiteral] = Field(default=None)


class ProgressPatch(BaseModel):
    mark_latest: Optional[bool] = None
    last_read: Optional[int] = None
    decrement: Optional[int] = None


class StatusPatch(BaseModel):
    status: StatusLiteral

