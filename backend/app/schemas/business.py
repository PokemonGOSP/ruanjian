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
    """FR-11：R02 创建活动申请。时间字段为不带时区的本地时间，与数据库 DATETIME 一致。"""

    club_id: int
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=5000)
    location: str = Field(min_length=1, max_length=255)
    starts_at: datetime
    ends_at: datetime
    registration_deadline: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=100000)
    budget: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class ActivityUpdateRequest(BaseModel):
    """FR-11：仅草稿/已撤回状态可编辑；未出现的字段保持原值。"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=5000)
    location: str | None = Field(default=None, min_length=1, max_length=255)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    registration_deadline: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=100000)
    budget: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)


class ActivityEndRequest(BaseModel):
    """FR-16：活动结束时可选填写活动总结。"""

    summary: str | None = Field(default=None, max_length=5000)
