from datetime import datetime

from pydantic import BaseModel


class ActivityData(BaseModel):
    """M04 活动响应资源。审核状态与执行状态保持两个独立字段。"""

    id: int
    club_id: int
    created_by: int
    title: str
    description: str
    location: str
    starts_at: datetime
    ends_at: datetime
    registration_deadline: datetime | None = None
    capacity: int | None = None
    budget: float = 0
    review_status: str
    execution_status: str
    review_comment: str | None = None
    reviewed_by: int | None = None
    cancellation_reason: str | None = None
    summary: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    registration_count: int = 0
    my_registration_status: str | None = None


class RegistrationUserData(BaseModel):
    id: int
    username: str
    display_name: str


class RegistrationData(BaseModel):
    id: int
    activity_id: int
    user_id: int
    status: str
    registered_at: datetime | None = None
    cancelled_at: datetime | None = None
    user: RegistrationUserData | None = None
