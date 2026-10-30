"""M02 社团注册、社团资料与年审的领域 Schema。

路径与 method 沿用 `docs/api/API_CONTRACT_V0_1.md`，本文件只细化请求/响应字段，
不改变 FR-03～FR-07 的语义、状态名称或资源归属。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReviewStatusValue = Literal["DRAFT", "PENDING", "APPROVED", "REJECTED", "WITHDRAWN"]


def _strip_required(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("不能为空")
    return text


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


class ClubRegistrationCreateRequest(BaseModel):
    proposed_name: str = Field(min_length=1, max_length=150)
    description: str = Field(min_length=1, max_length=10000)
    advisor_contact: str | None = Field(default=None, max_length=255)

    @field_validator("proposed_name", "description")
    @classmethod
    def required_text(cls, value: str) -> str:
        return _strip_required(value)

    @field_validator("advisor_contact")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class ClubRegistrationUpdateRequest(BaseModel):
    proposed_name: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=10000)
    advisor_contact: str | None = Field(default=None, max_length=255)

    @field_validator("proposed_name", "description")
    @classmethod
    def required_text_or_none(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("字段不能为 null")
        return _strip_required(value)

    @field_validator("advisor_contact")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class ClubUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=10000)
    advisor_contact: str | None = Field(default=None, max_length=255)

    @field_validator("name", "description")
    @classmethod
    def required_text_or_none(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("字段不能为 null")
        return _strip_required(value)

    @field_validator("advisor_contact")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _strip_optional(value)


class AnnualReviewCreateRequest(BaseModel):
    club_id: int = Field(ge=1)
    review_year: int = Field(ge=2000, le=2100)
    materials: str = Field(min_length=1, max_length=20000)

    @field_validator("materials")
    @classmethod
    def required_text(cls, value: str) -> str:
        return _strip_required(value)


class AnnualReviewUpdateRequest(BaseModel):
    review_year: int | None = Field(default=None, ge=2000, le=2100)
    materials: str | None = Field(default=None, max_length=20000)

    @field_validator("materials")
    @classmethod
    def required_text_or_none(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("字段不能为 null")
        return _strip_required(value)


class ClubRegistrationApplicationData(BaseModel):
    id: int
    applicant_user_id: int
    applicant_display_name: str | None = None
    proposed_name: str
    description: str
    advisor_contact: str | None = None
    review_status: ReviewStatusValue
    review_comment: str | None = None
    reviewed_by: int | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClubData(BaseModel):
    id: int
    registration_application_id: int
    name: str
    description: str
    advisor_contact: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ClubAuthorizationData(BaseModel):
    club_id: int
    user_id: int
    role_code: Literal["R02"] = "R02"


class ClubRegistrationReviewResult(BaseModel):
    application: ClubRegistrationApplicationData
    club: ClubData | None = None
    club_authorization: ClubAuthorizationData | None = None


class AnnualReviewData(BaseModel):
    id: int
    club_id: int
    club_name: str | None = None
    review_year: int
    submitted_by: int
    submitter_display_name: str | None = None
    materials: str
    review_status: ReviewStatusValue
    review_comment: str | None = None
    reviewed_by: int | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
