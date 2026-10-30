from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, select, update

from app.api.deps import CurrentPrincipal, DbSession
from app.core.exceptions import AppError
from app.core.permissions import require_system_role
from app.db.models.domain import Notification, ReadStatus
from app.schemas.common import ApiResponse, PageData
from app.schemas.notification import (
    ManagementNotificationRequest,
    NotificationBatchResult,
    NotificationData,
)
from app.services import audit_service, notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_data(row: Notification) -> dict:
    return {
        "id": row.id,
        "recipient_user_id": row.recipient_user_id,
        "title": row.title,
        "content": row.content,
        "event_type": row.event_type,
        "related_type": row.related_type,
        "related_id": row.related_id,
        "read_status": row.read_status,
        "created_at": row.created_at,
        "read_at": row.read_at,
    }


@router.get("", response_model=ApiResponse[PageData[NotificationData]])
def list_notifications(
    principal: CurrentPrincipal,
    db: DbSession,
    read_status: Literal["UNREAD", "READ"] | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    conditions = [Notification.recipient_user_id == principal.user_id]
    if read_status is not None:
        conditions.append(Notification.read_status == ReadStatus(read_status))
    total = db.scalar(select(func.count()).select_from(Notification).where(*conditions)) or 0
    rows = db.scalars(
        select(Notification)
        .where(*conditions)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [_to_data(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": int(total),
        },
    }


@router.post("/read-all", response_model=ApiResponse[dict])
def mark_all_read(principal: CurrentPrincipal, db: DbSession) -> dict:
    db.execute(
        update(Notification)
        .where(
            Notification.recipient_user_id == principal.user_id,
            Notification.read_status == ReadStatus.UNREAD,
        )
        .values(read_status=ReadStatus.READ, read_at=datetime.now())
    )
    db.commit()
    return {"code": 0, "message": "success", "data": {}}


@router.post("/management", response_model=ApiResponse[NotificationBatchResult])
def publish_management_notification(
    body: ManagementNotificationRequest,
    principal: CurrentPrincipal,
    db: DbSession,
    request: Request,
) -> dict:
    require_system_role(principal, "R03")
    count = notification_service.publish_management_notice(db, body)
    audit_service.record_audit(
        db,
        actor_user_id=principal.user_id,
        action="MANAGEMENT_NOTIFICATION_PUBLISHED",
        resource_type="notification",
        detail={
            "target_type": body.target_type,
            "recipient_count": count,
            "title": body.title,
        },
        ip_address=audit_service.request_ip(request),
    )
    db.commit()
    return {
        "code": 0,
        "message": "success",
        "data": {
            "created_count": count,
            "recipient_count": count,
            "target_type": body.target_type,
        },
    }


@router.post("/{notification_id}/read", response_model=ApiResponse[NotificationData])
def mark_read(notification_id: int, principal: CurrentPrincipal, db: DbSession) -> dict:
    row = db.get(Notification, notification_id)
    if row is None:
        raise AppError(40401, "通知不存在", 404)
    if row.recipient_user_id != principal.user_id:
        raise AppError(40301, "只能操作本人通知", 403)
    if row.read_status == ReadStatus.UNREAD:
        row.read_status = ReadStatus.READ
        row.read_at = datetime.now()
        db.commit()
        db.refresh(row)
    return {"code": 0, "message": "success", "data": _to_data(row)}
