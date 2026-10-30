from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.datetime_utils import naive_utc
from app.db.models.domain import FinanceType, RecordStatus


def _validate_amount(value: object) -> object:
    """Validate raw input so validation errors stay JSON serializable (no Decimal input)."""
    if value is None:
        return value
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError("金额必须大于 0")
    _, digits, exponent = parsed.as_tuple()
    if len(digits) > 12 or (exponent is not None and exponent < -2):
        raise ValueError("金额最多 12 位、2 位小数")
    return value


class FinanceRecordCreateRequest(BaseModel):
    club_id: int = Field(gt=0)
    activity_id: int | None = Field(default=None, gt=0)
    record_type: Literal["INCOME", "EXPENSE"]
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    occurred_on: datetime
    description: str = Field(min_length=1, max_length=500)
    voucher_reference: str | None = Field(default=None, max_length=255)

    @field_validator("occurred_on")
    @classmethod
    def _normalize_occurred_on(cls, value: datetime) -> datetime:
        return naive_utc(value)

    @field_validator("amount", mode="before")
    @classmethod
    def _positive_amount(cls, value: object) -> object:
        return _validate_amount(value)


class FinanceRecordUpdateRequest(BaseModel):
    """PATCH body: only supplied fields are changed; explicit null clears optional values."""

    activity_id: int | None = Field(default=None, gt=0)
    record_type: Literal["INCOME", "EXPENSE"] | None = None
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    occurred_on: datetime | None = None
    description: str | None = Field(default=None, min_length=1, max_length=500)
    voucher_reference: str | None = Field(default=None, max_length=255)

    @field_validator("occurred_on")
    @classmethod
    def _normalize_occurred_on(cls, value: datetime | None) -> datetime | None:
        return naive_utc(value) if value is not None else None

    @field_validator("amount", mode="before")
    @classmethod
    def _positive_amount(cls, value: object) -> object:
        return _validate_amount(value)


class FinanceRecordData(BaseModel):
    id: int
    club_id: int
    club_name: str
    activity_id: int | None = None
    activity_title: str | None = None
    record_type: FinanceType
    amount: Decimal
    occurred_on: datetime
    description: str
    voucher_reference: str | None = None
    status: RecordStatus
    created_by: int
    created_by_name: str | None = None
    voided_by: int | None = None
    voided_by_name: str | None = None
    void_reason: str | None = None
    created_at: datetime | None = None


class FinanceSummaryData(BaseModel):
    club_id: int | None = None
    club_ids: list[int] = Field(default_factory=list)
    income_total: Decimal
    expense_total: Decimal
    balance: Decimal
    active_record_count: int
    voided_record_count: int
