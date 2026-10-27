from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, aliased

from app.core.datetime_utils import day_end_exclusive, day_start
from app.core.exceptions import AppError
from app.core.permissions import Principal
from app.db.models.domain import Activity, Club, FinanceRecord, FinanceType, RecordStatus, User
from app.schemas.finance import FinanceRecordCreateRequest, FinanceRecordUpdateRequest
from app.services.audit_service import record_audit
from app.services.club_scope import require_leader_for_club, resolve_club_scope

CSV_HEADERS = [
    "记录ID",
    "社团",
    "活动",
    "类型",
    "金额",
    "发生日期",
    "说明",
    "凭证附件信息",
    "状态",
    "创建人",
    "作废人",
    "作废原因",
    "创建时间",
]

_TYPE_LABELS = {FinanceType.INCOME.value: "收入", FinanceType.EXPENSE.value: "支出"}
_STATUS_LABELS = {RecordStatus.ACTIVE.value: "有效", RecordStatus.VOIDED.value: "已作废"}
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _base_query() -> Select:
    creator = aliased(User)
    voider = aliased(User)
    return (
        select(
            FinanceRecord,
            Club.name.label("club_name"),
            Activity.title.label("activity_title"),
            creator.display_name.label("created_by_name"),
            voider.display_name.label("voided_by_name"),
        )
        .join(Club, Club.id == FinanceRecord.club_id)
        .outerjoin(Activity, Activity.id == FinanceRecord.activity_id)
        .outerjoin(creator, creator.id == FinanceRecord.created_by)
        .outerjoin(voider, voider.id == FinanceRecord.voided_by)
    )


def _conditions(
    scope: list[int] | None,
    *,
    club_id: int | None,
    activity_id: int | None,
    record_type: str | None,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
) -> list[Any]:
    conditions: list[Any] = []
    if scope is not None:
        conditions.append(FinanceRecord.club_id.in_(scope))
    if club_id is not None:
        conditions.append(FinanceRecord.club_id == club_id)
    if activity_id is not None:
        conditions.append(FinanceRecord.activity_id == activity_id)
    if record_type is not None:
        conditions.append(FinanceRecord.record_type == FinanceType(record_type))
    if status is not None:
        conditions.append(FinanceRecord.status == RecordStatus(status))
    start = day_start(date_from)
    end = day_end_exclusive(date_to)
    if start is not None:
        conditions.append(FinanceRecord.occurred_on >= start)
    if end is not None:
        conditions.append(FinanceRecord.occurred_on < end)
    return conditions


def _apply_where(stmt: Select, conditions: list[Any]) -> Select:
    return stmt.where(*conditions) if conditions else stmt


def _serialize_row(row: Any) -> dict[str, Any]:
    record, club_name, activity_title, created_by_name, voided_by_name = row
    return {
        "id": record.id,
        "club_id": record.club_id,
        "club_name": club_name,
        "activity_id": record.activity_id,
        "activity_title": activity_title,
        "record_type": record.record_type,
        "amount": record.amount,
        "occurred_on": record.occurred_on,
        "description": record.description,
        "voucher_reference": record.voucher_reference,
        "status": record.status,
        "created_by": record.created_by,
        "created_by_name": created_by_name,
        "voided_by": record.voided_by,
        "voided_by_name": voided_by_name,
        "void_reason": record.void_reason,
        "created_at": record.created_at,
    }


def _serialize_record(db: Session, record: FinanceRecord) -> dict[str, Any]:
    club = db.get(Club, record.club_id)
    activity = db.get(Activity, record.activity_id) if record.activity_id is not None else None
    creator = db.get(User, record.created_by)
    voider = db.get(User, record.voided_by) if record.voided_by is not None else None
    return {
        "id": record.id,
        "club_id": record.club_id,
        "club_name": club.name if club is not None else "",
        "activity_id": record.activity_id,
        "activity_title": activity.title if activity is not None else None,
        "record_type": record.record_type,
        "amount": record.amount,
        "occurred_on": record.occurred_on,
        "description": record.description,
        "voucher_reference": record.voucher_reference,
        "status": record.status,
        "created_by": record.created_by,
        "created_by_name": creator.display_name if creator is not None else None,
        "voided_by": record.voided_by,
        "voided_by_name": voider.display_name if voider is not None else None,
        "void_reason": record.void_reason,
        "created_at": record.created_at,
    }


def list_records(
    db: Session,
    principal: Principal,
    *,
    club_id: int | None = None,
    activity_id: int | None = None,
    record_type: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    scope = resolve_club_scope(db, principal, club_id)
    conditions = _conditions(
        scope,
        club_id=club_id,
        activity_id=activity_id,
        record_type=record_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    total = db.scalar(_apply_where(select(func.count()).select_from(FinanceRecord), conditions)) or 0
    stmt = _apply_where(_base_query(), conditions).order_by(
        FinanceRecord.occurred_on.desc(),
        FinanceRecord.id.desc(),
    )
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return [_serialize_row(row) for row in rows], int(total)


def _all_records(
    db: Session,
    scope: list[int] | None,
    *,
    club_id: int | None,
    activity_id: int | None,
    record_type: str | None,
    status: str | None,
    date_from: date | None,
    date_to: date | None,
) -> list[dict[str, Any]]:
    conditions = _conditions(
        scope,
        club_id=club_id,
        activity_id=activity_id,
        record_type=record_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    stmt = _apply_where(_base_query(), conditions).order_by(
        FinanceRecord.occurred_on.desc(),
        FinanceRecord.id.desc(),
    )
    return [_serialize_row(row) for row in db.execute(stmt).all()]


def totals(
    db: Session,
    scope: list[int] | None,
    *,
    club_id: int | None,
    date_from: date | None,
    date_to: date | None,
) -> dict[str, Any]:
    conditions = _conditions(
        scope,
        club_id=club_id,
        activity_id=None,
        record_type=None,
        status=None,
        date_from=date_from,
        date_to=date_to,
    )
    active_conditions = conditions + [FinanceRecord.status == RecordStatus.ACTIVE]

    def amount_total(record_type: FinanceType) -> Decimal:
        value = db.scalar(
            _apply_where(
                select(func.coalesce(func.sum(FinanceRecord.amount), 0)),
                active_conditions + [FinanceRecord.record_type == record_type],
            )
        )
        return Decimal(value or 0)

    active_count = db.scalar(
        _apply_where(select(func.count()).select_from(FinanceRecord), active_conditions)
    ) or 0
    voided_count = db.scalar(
        _apply_where(
            select(func.count()).select_from(FinanceRecord),
            conditions + [FinanceRecord.status == RecordStatus.VOIDED],
        )
    ) or 0

    income_total = amount_total(FinanceType.INCOME)
    expense_total = amount_total(FinanceType.EXPENSE)
    if scope is None:
        club_ids = list(db.scalars(select(Club.id).order_by(Club.id)).all())
    else:
        club_ids = list(scope)
    return {
        "club_id": club_id,
        "club_ids": club_ids,
        "income_total": income_total,
        "expense_total": expense_total,
        "balance": income_total - expense_total,
        "active_record_count": int(active_count),
        "voided_record_count": int(voided_count),
    }


def summarize(
    db: Session,
    principal: Principal,
    *,
    club_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    scope = resolve_club_scope(db, principal, club_id)
    return totals(db, scope, club_id=club_id, date_from=date_from, date_to=date_to)


def create_record(
    db: Session,
    principal: Principal,
    body: FinanceRecordCreateRequest,
    *,
    ip_address: str | None = None,
) -> dict[str, Any]:
    require_leader_for_club(principal, body.club_id)
    club = db.get(Club, body.club_id)
    if club is None:
        raise AppError(40401, "社团不存在", 404)

    activity = None
    if body.activity_id is not None:
        activity = db.get(Activity, body.activity_id)
        if activity is None or activity.club_id != body.club_id:
            raise AppError(40002, "关联活动不属于目标社团", 400)

    record = FinanceRecord(
        club_id=body.club_id,
        activity_id=body.activity_id,
        record_type=FinanceType(body.record_type),
        amount=body.amount,
        occurred_on=body.occurred_on,
        description=body.description,
        voucher_reference=body.voucher_reference,
        status=RecordStatus.ACTIVE,
        created_by=principal.user_id,
    )
    db.add(record)
    db.flush()
    record_audit(
        db,
        actor_user_id=principal.user_id,
        action="FINANCE_RECORD_CREATED",
        resource_type="finance_record",
        resource_id=record.id,
        detail={
            "club_id": record.club_id,
            "activity_id": record.activity_id,
            "record_type": record.record_type.value,
            "amount": str(record.amount),
        },
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(record)
    return _serialize_record(db, record)


def update_record(
    db: Session,
    principal: Principal,
    record_id: int,
    body: FinanceRecordUpdateRequest,
    *,
    ip_address: str | None = None,
) -> dict[str, Any]:
    record = db.get(FinanceRecord, record_id)
    if record is None:
        raise AppError(40401, "经费记录不存在", 404)
    require_leader_for_club(principal, record.club_id)
    if record.status != RecordStatus.ACTIVE:
        raise AppError(40901, "已作废的经费记录不能修改", 409)

    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise AppError(40002, "没有可更新的字段", 400)
    for field in ("record_type", "amount", "occurred_on", "description"):
        if field in updates and updates[field] is None:
            raise AppError(40002, f"{field} 不能为空", 400)

    if "activity_id" in updates and updates["activity_id"] is not None:
        activity = db.get(Activity, updates["activity_id"])
        if activity is None or activity.club_id != record.club_id:
            raise AppError(40002, "关联活动不属于目标社团", 400)

    if "record_type" in updates:
        record.record_type = FinanceType(updates.pop("record_type"))
    for field in ("activity_id", "amount", "occurred_on", "description", "voucher_reference"):
        if field in updates:
            setattr(record, field, updates.pop(field))

    record_audit(
        db,
        actor_user_id=principal.user_id,
        action="FINANCE_RECORD_UPDATED",
        resource_type="finance_record",
        resource_id=record.id,
        detail={"changed": sorted(body.model_fields_set)},
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(record)
    return _serialize_record(db, record)


def void_record(
    db: Session,
    principal: Principal,
    record_id: int,
    reason: str,
    *,
    ip_address: str | None = None,
) -> dict[str, Any]:
    record = db.get(FinanceRecord, record_id)
    if record is None:
        raise AppError(40401, "经费记录不存在", 404)
    require_leader_for_club(principal, record.club_id)
    if record.status != RecordStatus.ACTIVE:
        raise AppError(40901, "该经费记录已作废", 409)

    record.status = RecordStatus.VOIDED
    record.voided_by = principal.user_id
    record.void_reason = reason
    record_audit(
        db,
        actor_user_id=principal.user_id,
        action="FINANCE_RECORD_VOIDED",
        resource_type="finance_record",
        resource_id=record.id,
        detail={"reason": reason},
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(record)
    return _serialize_record(db, record)


def _safe_cell(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


def _money(value: Any) -> str:
    return f"{Decimal(value or 0):.2f}"


def _datetime_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d %H:%M:%S") if value is not None else ""


def _date_text(value: Any) -> str:
    return value.strftime("%Y-%m-%d") if value is not None else ""


def build_csv(
    records: Sequence[dict[str, Any]],
    summary: dict[str, Any],
    *,
    scope_label: str,
    generated_at: str,
) -> bytes:
    """Build an Excel-friendly CSV (UTF-8 BOM, CRLF) with formula injection defense."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(["经费汇总"])
    writer.writerow(["社团范围", _safe_cell(scope_label)])
    writer.writerow(["收入合计", _money(summary["income_total"])])
    writer.writerow(["支出合计", _money(summary["expense_total"])])
    writer.writerow(["结余", _money(summary["balance"])])
    writer.writerow(["有效记录数", summary["active_record_count"]])
    writer.writerow(["已作废记录数", summary["voided_record_count"]])
    writer.writerow(["生成时间", generated_at])
    writer.writerow([])
    writer.writerow(CSV_HEADERS)
    for item in records:
        writer.writerow(
            [
                item["id"],
                _safe_cell(item["club_name"]),
                _safe_cell(item["activity_title"]),
                _TYPE_LABELS.get(_enum_value(item["record_type"]), _enum_value(item["record_type"])),
                _money(item["amount"]),
                _date_text(item["occurred_on"]),
                _safe_cell(item["description"]),
                _safe_cell(item["voucher_reference"]),
                _STATUS_LABELS.get(_enum_value(item["status"]), _enum_value(item["status"])),
                _safe_cell(item["created_by_name"]),
                _safe_cell(item["voided_by_name"]),
                _safe_cell(item["void_reason"]),
                _datetime_text(item["created_at"]),
            ]
        )
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def export_csv(
    db: Session,
    principal: Principal,
    *,
    club_id: int | None = None,
    activity_id: int | None = None,
    record_type: str | None = None,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[bytes, str]:
    scope = resolve_club_scope(db, principal, club_id)
    summary = totals(db, scope, club_id=club_id, date_from=date_from, date_to=date_to)
    records = _all_records(
        db,
        scope,
        club_id=club_id,
        activity_id=activity_id,
        record_type=record_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    if scope is None:
        scope_label = "全部社团"
    else:
        names = list(db.scalars(select(Club.name).where(Club.id.in_(scope)).order_by(Club.id)).all())
        scope_label = "、".join(names) if names else "无"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return build_csv(records, summary, scope_label=scope_label, generated_at=generated_at), "finance-records.csv"
