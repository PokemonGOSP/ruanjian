from datetime import date
from typing import Literal

from fastapi import APIRouter, Query, Request

from app.api.deps import CurrentPrincipal, DbSession
from app.schemas.business import ReasonRequest
from app.schemas.common import ApiResponse, PageData
from app.schemas.finance import (
    FinanceRecordCreateRequest,
    FinanceRecordData,
    FinanceRecordUpdateRequest,
    FinanceSummaryData,
)
from app.services import audit_service, finance_service
from app.services.club_scope import require_leader_for_club

router = APIRouter(prefix="/finance-records", tags=["finance"])


@router.get("/summary", response_model=ApiResponse[FinanceSummaryData])
def finance_summary(
    principal: CurrentPrincipal,
    db: DbSession,
    club_id: int | None = Query(default=None, gt=0),
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    data = finance_service.summarize(db, principal, club_id=club_id, date_from=date_from, date_to=date_to)
    return {"code": 0, "message": "success", "data": data}


@router.post("", response_model=ApiResponse[FinanceRecordData], status_code=201)
def create_finance_record(
    body: FinanceRecordCreateRequest,
    principal: CurrentPrincipal,
    db: DbSession,
    request: Request,
) -> dict:
    require_leader_for_club(principal, body.club_id)
    data = finance_service.create_record(
        db,
        principal,
        body,
        ip_address=audit_service.request_ip(request),
    )
    return {"code": 0, "message": "success", "data": data}


@router.get("", response_model=ApiResponse[PageData[FinanceRecordData]])
def list_finance_records(
    principal: CurrentPrincipal,
    db: DbSession,
    club_id: int | None = Query(default=None, gt=0),
    activity_id: int | None = Query(default=None, gt=0),
    record_type: Literal["INCOME", "EXPENSE"] | None = None,
    status: Literal["ACTIVE", "VOIDED"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    items, total = finance_service.list_records(
        db,
        principal,
        club_id=club_id,
        activity_id=activity_id,
        record_type=record_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return {
        "code": 0,
        "message": "success",
        "data": {"items": items, "page": page, "page_size": page_size, "total": total},
    }


@router.patch("/{record_id}", response_model=ApiResponse[FinanceRecordData])
def update_finance_record(
    record_id: int,
    body: FinanceRecordUpdateRequest,
    principal: CurrentPrincipal,
    db: DbSession,
    request: Request,
) -> dict:
    data = finance_service.update_record(
        db,
        principal,
        record_id,
        body,
        ip_address=audit_service.request_ip(request),
    )
    return {"code": 0, "message": "success", "data": data}


@router.post("/{record_id}/void", response_model=ApiResponse[FinanceRecordData])
def void_finance_record(
    record_id: int,
    body: ReasonRequest,
    principal: CurrentPrincipal,
    db: DbSession,
    request: Request,
) -> dict:
    data = finance_service.void_record(
        db,
        principal,
        record_id,
        body.reason,
        ip_address=audit_service.request_ip(request),
    )
    return {"code": 0, "message": "success", "data": data}
