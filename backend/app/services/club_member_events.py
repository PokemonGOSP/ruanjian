"""M02/M03 业务事件的站内通知与审计写入。

边界说明：
- FR-19 的查询/已读接口由 M06 owner 实现；本模块只负责在 M02/M03 业务事务内写入
  `notifications` 记录，保证审核结果、申请提交等事件不会因为 M06 尚未完成而丢失。
- FR-22 的审计查询由 M07 owner 实现；本模块只写入 `audit_logs` 记录。
- 不修改 Notification/AuditLog 模型，也不新增公共响应结构。
"""

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.domain import (
    AccountStatus,
    AuditLog,
    ClubRoleAssignment,
    Notification,
    ReadStatus,
    SystemRoleAssignment,
    User,
)


def _active_manager_ids(db: Session) -> list[int]:
    return list(
        db.scalars(
            select(SystemRoleAssignment.user_id)
            .join(User, User.id == SystemRoleAssignment.user_id)
            .where(
                SystemRoleAssignment.role_code == "R03",
                SystemRoleAssignment.active.is_(True),
                User.status == AccountStatus.NORMAL,
            )
        ).all()
    )


def _active_club_leader_ids(db: Session, club_id: int) -> list[int]:
    return list(
        db.scalars(
            select(ClubRoleAssignment.user_id)
            .join(User, User.id == ClubRoleAssignment.user_id)
            .where(
                ClubRoleAssignment.club_id == club_id,
                ClubRoleAssignment.role_code == "R02",
                ClubRoleAssignment.active.is_(True),
                User.status == AccountStatus.NORMAL,
            )
        ).all()
    )


def add_notification(
    db: Session,
    *,
    recipient_user_id: int,
    title: str,
    content: str,
    event_type: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> Notification:
    notification = Notification(
        recipient_user_id=recipient_user_id,
        title=title[:200],
        content=content,
        event_type=event_type[:50],
        related_type=related_type[:50] if related_type else None,
        related_id=related_id,
        read_status=ReadStatus.UNREAD,
    )
    db.add(notification)
    return notification


def notify_managers(
    db: Session,
    *,
    title: str,
    content: str,
    event_type: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    for user_id in sorted(set(_active_manager_ids(db))):
        add_notification(
            db,
            recipient_user_id=user_id,
            title=title,
            content=content,
            event_type=event_type,
            related_type=related_type,
            related_id=related_id,
        )


def notify_club_leaders(
    db: Session,
    club_id: int,
    *,
    title: str,
    content: str,
    event_type: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    for user_id in sorted(set(_active_club_leader_ids(db, club_id))):
        add_notification(
            db,
            recipient_user_id=user_id,
            title=title,
            content=content,
            event_type=event_type,
            related_type=related_type,
            related_id=related_id,
        )


def notify_user(
    db: Session,
    user_id: int,
    *,
    title: str,
    content: str,
    event_type: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> None:
    add_notification(
        db,
        recipient_user_id=user_id,
        title=title,
        content=content,
        event_type=event_type,
        related_type=related_type,
        related_id=related_id,
    )


def record_audit(
    db: Session,
    *,
    actor_user_id: int,
    action: str,
    resource_type: str,
    resource_id: int | str | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action[:100],
            resource_type=resource_type[:100],
            resource_id=str(resource_id) if resource_id is not None else None,
            detail_json=json.dumps(detail, ensure_ascii=False, default=str) if detail is not None else None,
        )
    )
