from __future__ import annotations

import json
from datetime import date
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.core.datetime_utils import day_end_exclusive, day_start
from app.core.permissions import Principal
from app.db.models.domain import (
    Activity,
    ActivityExecutionStatus,
    ActivityRegistration,
    AuditLog,
    Club,
    ClubMember,
    MemberStatus,
    RegistrationStatus,
    ReviewStatus,
    User,
)
from app.services.club_scope import resolve_club_scope
from app.services.finance_service import totals


def _apply_where(stmt: Select, conditions: list[Any]) -> Select:
    return stmt.where(*conditions) if conditions else stmt


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _zero_filled(values: list[Any]) -> dict[str, int]:
    return {_enum_value(value): 0 for value in values}


def build_summary(
    db: Session,
    principal: Principal,
    *,
    club_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    scope = resolve_club_scope(db, principal, club_id)
    start = day_start(date_from)
    end = day_end_exclusive(date_to)

    club_conditions: list[Any] = []
    if scope is not None:
        club_conditions.append(Club.id.in_(scope))
    if club_id is not None:
        club_conditions.append(Club.id == club_id)
    club_count = db.scalar(_apply_where(select(func.count()).select_from(Club), club_conditions)) or 0

    member_conditions: list[Any] = [ClubMember.status == MemberStatus.ACTIVE]
    if scope is not None:
        member_conditions.append(ClubMember.club_id.in_(scope))
    if club_id is not None:
        member_conditions.append(ClubMember.club_id == club_id)
    member_count = db.scalar(_apply_where(select(func.count()).select_from(ClubMember), member_conditions)) or 0

    activity_conditions: list[Any] = []
    if scope is not None:
        activity_conditions.append(Activity.club_id.in_(scope))
    if club_id is not None:
        activity_conditions.append(Activity.club_id == club_id)
    if start is not None:
        activity_conditions.append(Activity.starts_at >= start)
    if end is not None:
        activity_conditions.append(Activity.starts_at < end)

    activity_count = db.scalar(_apply_where(select(func.count()).select_from(Activity), activity_conditions)) or 0

    review_counts = _zero_filled(list(ReviewStatus))
    review_rows = db.execute(
        _apply_where(
            select(Activity.review_status, func.count()).select_from(Activity),
            activity_conditions,
        ).group_by(Activity.review_status)
    ).all()
    for status_value, count in review_rows:
        review_counts[_enum_value(status_value)] = int(count)

    execution_counts = _zero_filled(list(ActivityExecutionStatus))
    execution_rows = db.execute(
        _apply_where(
            select(Activity.execution_status, func.count()).select_from(Activity),
            activity_conditions,
        ).group_by(Activity.execution_status)
    ).all()
    for status_value, count in execution_rows:
        execution_counts[_enum_value(status_value)] = int(count)

    registration_conditions: list[Any] = [
        ActivityRegistration.status == RegistrationStatus.REGISTERED,
        *activity_conditions,
    ]
    registration_count = db.scalar(
        select(func.count())
        .select_from(ActivityRegistration)
        .join(Activity, Activity.id == ActivityRegistration.activity_id)
        .where(*registration_conditions)
    ) or 0

    finance = totals(db, scope, club_id=club_id, date_from=date_from, date_to=date_to)
    if scope is None:
        club_ids = list(db.scalars(select(Club.id).order_by(Club.id)).all())
    else:
        club_ids = list(scope)

    return {
        "club_id": club_id,
        "club_ids": club_ids,
        "date_from": date_from,
        "date_to": date_to,
        "club_count": int(club_count),
        "member_count": int(member_count),
        "activity_count": int(activity_count),
        "registration_count": int(registration_count),
        "activity_by_review_status": review_counts,
        "activity_by_execution_status": execution_counts,
        "finance_income_total": finance["income_total"],
        "finance_expense_total": finance["expense_total"],
        "finance_balance": finance["balance"],
        "finance_voided_count": finance["voided_record_count"],
    }


def _parse_detail(raw: str | None) -> Any | None:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def list_audit_logs(
    db: Session,
    *,
    actor_user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    conditions: list[Any] = []
    if actor_user_id is not None:
        conditions.append(AuditLog.actor_user_id == actor_user_id)
    if action:
        conditions.append(AuditLog.action == action)
    if resource_type:
        conditions.append(AuditLog.resource_type == resource_type)
    start = day_start(date_from)
    end = day_end_exclusive(date_to)
    if start is not None:
        conditions.append(AuditLog.created_at >= start)
    if end is not None:
        conditions.append(AuditLog.created_at < end)

    total = db.scalar(_apply_where(select(func.count()).select_from(AuditLog), conditions)) or 0
    actor = aliased(User)
    stmt = select(
        AuditLog.id.label("id"),
        AuditLog.actor_user_id.label("actor_user_id"),
        actor.username.label("actor_username"),
        AuditLog.action.label("action"),
        AuditLog.resource_type.label("resource_type"),
        AuditLog.resource_id.label("resource_id"),
        AuditLog.detail_json.label("detail_json"),
        AuditLog.ip_address.label("ip_address"),
        AuditLog.created_at.label("created_at"),
    ).outerjoin(actor, actor.id == AuditLog.actor_user_id)
    stmt = _apply_where(stmt, conditions).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    items = [
        {
            "id": row.id,
            "actor_user_id": row.actor_user_id,
            "actor_username": row.actor_username,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "detail": _parse_detail(row.detail_json),
            "ip_address": row.ip_address,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return items, int(total)
