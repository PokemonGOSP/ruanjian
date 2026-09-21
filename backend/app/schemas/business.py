from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class PayloadRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)


class ReviewRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    comment: str | None = Field(default=None, max_length=2000)


class ReasonRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=2000)


class RoleAssignmentRequest(BaseModel):
    role_code: Literal["R02", "R03", "R04"]
    club_id: int | None = None


class AccountCreateRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class AccountUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    status: Literal["NORMAL", "DISABLED"] | None = None


class ActivityCreateRequest(BaseModel):
    club_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str
    location: str = Field(min_length=1, max_length=255)
    starts_at: datetime
    ends_at: datetime
    registration_deadline: datetime | None = None
    capacity: int | None = Field(default=None, ge=1)
    budget: Decimal = Field(default=Decimal("0"), ge=0)
