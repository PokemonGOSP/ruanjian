"""M03 入团/退出申请、成员名册与社团职务的领域 Schema。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MembershipApplicationStatusValue = Literal["PENDING", "APPROVED", "REJECTED", "WITHDRAWN"]
MembershipTypeValue = Literal["JOIN", "EXIT"]
MemberStatusValue = Literal["ACTIVE", "EXITED"]


class MembershipApplicationCreateRequest(BaseModel):
    club_id: int = Field(ge=1)
    application_type: MembershipTypeValue
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def optional_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class ClubMemberUpdateRequest(BaseModel):
    position_name: str | None = Field(default=None, max_length=100)

    @field_validator("position_name")
    @classmethod
    def optional_position(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class ClubMemberData(BaseModel):
    id: int
    club_id: int
    user_id: int | None = None
    username: str | None = None
    display_name: str
    position_name: str | None = None
    status: MemberStatusValue
    joined_at: datetime | None = None
    exited_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MembershipApplicationData(BaseModel):
    id: int
    club_id: int
    club_name: str | None = None
    applicant_user_id: int
    applicant_display_name: str | None = None
    application_type: MembershipTypeValue
    reason: str | None = None
    status: MembershipApplicationStatusValue
    processed_by: int | None = None
    processed_by_display_name: str | None = None
    process_comment: str | None = None
    created_at: datetime
    processed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class MembershipProcessResult(BaseModel):
    application: MembershipApplicationData
    member: ClubMemberData | None = None
