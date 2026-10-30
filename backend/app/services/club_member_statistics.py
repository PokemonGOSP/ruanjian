"""M07-A 社团/成员统计查询服务。

本模块不注册新的公共 URL；API Contract 只定义 `/reports/summary`，由 M07 owner
在聚合响应中调用本服务。权限与数据范围在服务内校验，避免绕过 R02/R03 边界。
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import Principal
from app.repositories import club_repository, member_repository


def club_member_statistics(
    db: Session,
    principal: Principal,
    *,
    club_id: int | None = None,
    review_year: int | None = None,
) -> dict:
    year = review_year or datetime.now().year
    if year < 2000 or year > 2100:
        raise AppError(40001, "review_year 超出允许范围", 422)

    if principal.has_system_role("R03"):
        scope = "ALL"
        if club_id is not None:
            club = club_repository.get_club(db, club_id)
            if club is None:
                raise AppError(40401, "社团不存在", 404)
            club_ids: list[int] | None = [club_id]
        else:
            club_ids = None
    elif principal.club_leader_ids:
        scope = "OWN_CLUBS"
        if club_id is not None and club_id not in principal.club_leader_ids:
            raise AppError(40302, "没有该社团的 R02 权限", 403)
        club_ids = [club_id] if club_id is not None else sorted(principal.club_leader_ids)
    else:
        raise AppError(40301, "需要 R03 或目标社团 R02 权限", 403)

    clubs = club_repository.all_clubs(db, club_ids)
    target_ids = [club.id for club in clubs]
    member_counts = member_repository.member_counts_by_club(db, target_ids)
    pending_counts = member_repository.pending_application_counts_by_club(db, target_ids)
    review_statuses = club_repository.annual_review_status_by_year(db, target_ids, year)

    items = []
    total_active_memberships = 0
    total_memberships = 0
    total_pending = 0
    for club in clubs:
        counts = member_counts.get(club.id, {"ACTIVE": 0, "EXITED": 0})
        active_count = int(counts.get("ACTIVE", 0))
        exited_count = int(counts.get("EXITED", 0))
        pending_count = int(pending_counts.get(club.id, 0))
        status = review_statuses.get(club.id)
        items.append(
            {
                "club_id": club.id,
                "club_name": club.name,
                "active_member_count": active_count,
                "exited_member_count": exited_count,
                "pending_membership_application_count": pending_count,
                "annual_review_status": status.value if status is not None else None,
            }
        )
        total_active_memberships += active_count
        total_memberships += active_count + exited_count
        total_pending += pending_count

    return {
        "scope": scope,
        "review_year": year,
        "total_clubs": len(clubs),
        "total_active_members": member_repository.distinct_active_member_count(db, target_ids),
        "total_active_memberships": total_active_memberships,
        "total_memberships": total_memberships,
        "total_pending_membership_applications": total_pending,
        "items": items,
        "generated_at": datetime.now(),
    }
