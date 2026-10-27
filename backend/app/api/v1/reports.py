from datetime import date
from typing import Literal

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentPrincipal, DbSession
from app.core.exceptions import AppError
from app.core.permissions import require_system_role
from app.schemas.common import ApiResponse, PageData
from app.schemas.report import AuditLogData, ReportSummaryData
from app.services import finance_service, report_service

router = APIRouter(tags=["reports"])


@router.get("/reports/summary", response_model=ApiResponse[ReportSummaryData])
def report_summary(
    principal: CurrentPrincipal,
    db: DbSession,
    club_id: int | None = Query(default=None, gt=0),
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict:
    data = report_service.build_summary(
        db,
        principal,
        club_id=club_id,
        date_from=date_from,
        date_to=date_to,
    )
    return {"code": 0, "message": "success", "data": data}


@router.get("/reports/export")
def export_report(
    principal: CurrentPrincipal,
    db: DbSession,
    format: str = "csv",
    club_id: int | None = Query(default=None, gt=0),
    activity_id: int | None = Query(default=None, gt=0),
    record_type: Literal["INCOME", "EXPENSE"] | None = None,
    status: Literal["ACTIVE", "VOIDED"] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Response:
    if format.lower() != "csv":
        raise AppError(40001, "仅支持 csv 导出格式", 422)
    content, filename = finance_service.export_csv(
        db,
        principal,
        club_id=club_id,
        activity_id=activity_id,
        record_type=record_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit-logs", response_model=ApiResponse[PageData[AuditLogData]])
def list_audit_logs(
    principal: CurrentPrincipal,
    db: DbSession,
    actor_user_id: int | None = Query(default=None, gt=0),
    action: str | None = Query(default=None, max_length=100),
    resource_type: str | None = Query(default=None, max_length=100),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    require_system_role(principal, "R04")
    items, total = report_service.list_audit_logs(
        db,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
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
