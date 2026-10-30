from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.db.models.domain import ReadStatus


class NotificationData(BaseModel):
    id: int
    recipient_user_id: int
    title: str
    content: str
    event_type: str
    related_type: str | None = None
    related_id: int | None = None
    read_status: ReadStatus
    created_at: datetime
    read_at: datetime | None = None


class ManagementNotificationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)
    target_type: Literal["USERS", "ROLES", "CLUBS"]
    user_ids: list[int] = Field(default_factory=list, max_length=500)
    role_codes: list[Literal["R01", "R02", "R03", "R04"]] = Field(default_factory=list, max_length=4)
    club_ids: list[int] = Field(default_factory=list, max_length=500)


class NotificationBatchResult(BaseModel):
    created_count: int
    recipient_count: int
    target_type: Literal["USERS", "ROLES", "CLUBS"]
