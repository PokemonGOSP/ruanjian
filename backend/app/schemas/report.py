from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class ReportSummaryData(BaseModel):
    club_id: int | None = None
    club_ids: list[int] = Field(default_factory=list)
    date_from: date | None = None
    date_to: date | None = None
    club_count: int
    member_count: int
    activity_count: int
    registration_count: int
    activity_by_review_status: dict[str, int]
    activity_by_execution_status: dict[str, int]
    finance_income_total: Decimal
    finance_expense_total: Decimal
    finance_balance: Decimal
    finance_voided_count: int


class AuditLogData(BaseModel):
    id: int
    actor_user_id: int | None = None
    actor_username: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    detail: Any | None = None
    ip_address: str | None = None
    created_at: datetime
