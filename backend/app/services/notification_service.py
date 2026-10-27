from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.db.models.domain import (
    Club,
    ClubMember,
    ClubRoleAssignment,
    MemberStatus,
    Notification,
    ReadStatus,
    SystemRoleAssignment,
    User,
)
from app.schemas.notification import ManagementNotificationRequest


def notify(
    db: Session,
    *,
    recipient_user_id: int,
    title: str,
    content: str,
    event_type: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> Notification:
    """FR-19 hook for business events implemented by other modules."""
    row = Notification(
        recipient_user_id=recipient_user_id,
        title=title,
        content=content,
        event_type=event_type,
        related_type=related_type,
        related_id=related_id,
        read_status=ReadStatus.UNREAD,
    )
    db.add(row)
    return row


def notify_many(
    db: Session,
    recipient_user_ids: list[int],
    *,
    title: str,
    content: str,
    event_type: str,
    related_type: str | None = None,
    related_id: int | None = None,
) -> list[Notification]:
    rows = [
        Notification(
            recipient_user_id=user_id,
            title=title,
            content=content,
            event_type=event_type,
            related_type=related_type,
            related_id=related_id,
            read_status=ReadStatus.UNREAD,
        )
        for user_id in sorted(set(recipient_user_ids))
    ]
    db.add_all(rows)
    return rows


def validate_management_request(body: ManagementNotificationRequest) -> None:
    """Reject mixed or empty target lists so one notice has one unambiguous audience."""
    if body.target_type == "USERS":
        if not body.user_ids:
            raise AppError(40002, "请至少指定一个目标用户", 400)
        if body.role_codes or body.club_ids:
            raise AppError(40002, "target_type=USERS 时不能同时指定角色或社团", 400)
    elif body.target_type == "ROLES":
        if not body.role_codes:
            raise AppError(40002, "请至少指定一个目标角色", 400)
        if body.user_ids or body.club_ids:
            raise AppError(40002, "target_type=ROLES 时不能同时指定用户或社团", 400)
    elif body.target_type == "CLUBS":
        if not body.club_ids:
            raise AppError(40002, "请至少指定一个目标社团", 400)
        if body.user_ids or body.role_codes:
            raise AppError(40002, "target_type=CLUBS 时不能同时指定用户或角色", 400)


def resolve_management_recipients(db: Session, body: ManagementNotificationRequest) -> list[int]:
    validate_management_request(body)

    if body.target_type == "USERS":
        user_ids = sorted(set(body.user_ids))
        found = set(db.scalars(select(User.id).where(User.id.in_(user_ids))).all())
        missing = [user_id for user_id in user_ids if user_id not in found]
        if missing:
            raise AppError(40002, f"目标用户不存在：{missing}", 400)
        return user_ids

    if body.target_type == "ROLES":
        roles = sorted(set(body.role_codes))
        recipients: set[int] = set()
        system_roles = [role for role in roles if role != "R02"]
        if system_roles:
            recipients.update(
                db.scalars(
                    select(SystemRoleAssignment.user_id).where(
                        SystemRoleAssignment.role_code.in_(system_roles),
                        SystemRoleAssignment.active.is_(True),
                    )
                ).all()
            )
        if "R02" in roles:
            recipients.update(
                db.scalars(
                    select(ClubRoleAssignment.user_id).where(
                        ClubRoleAssignment.role_code == "R02",
                        ClubRoleAssignment.active.is_(True),
                    )
                ).all()
            )
        if not recipients:
            raise AppError(40002, "目标角色当前没有可用接收人", 400)
        return sorted(recipients)

    club_ids = sorted(set(body.club_ids))
    found = set(db.scalars(select(Club.id).where(Club.id.in_(club_ids))).all())
    missing = [club_id for club_id in club_ids if club_id not in found]
    if missing:
        raise AppError(40002, f"目标社团不存在：{missing}", 400)

    members = set(
        db.scalars(
            select(ClubMember.user_id).where(
                ClubMember.club_id.in_(club_ids),
                ClubMember.status == MemberStatus.ACTIVE,
            )
        ).all()
    )
    leaders = set(
        db.scalars(
            select(ClubRoleAssignment.user_id).where(
                ClubRoleAssignment.club_id.in_(club_ids),
                ClubRoleAssignment.role_code == "R02",
                ClubRoleAssignment.active.is_(True),
            )
        ).all()
    )
    recipients = members | leaders
    if not recipients:
        raise AppError(40002, "目标社团当前没有可用接收人", 400)
    return sorted(recipients)


def publish_management_notice(db: Session, body: ManagementNotificationRequest) -> int:
    recipients = resolve_management_recipients(db, body)
    notify_many(
        db,
        recipients,
        title=body.title,
        content=body.content,
        event_type="MANAGEMENT_NOTICE",
        related_type="MANAGEMENT_NOTICE",
    )
    return len(recipients)
