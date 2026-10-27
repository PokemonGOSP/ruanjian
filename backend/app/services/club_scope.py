from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.permissions import Principal
from app.db.models.domain import Club


def resolve_club_scope(db: Session, principal: Principal, club_id: int | None) -> list[int] | None:
    """Return the club ids a principal may read, or None when R03 may read every club."""
    if club_id is not None:
        if db.get(Club, club_id) is None:
            raise AppError(40401, "社团不存在", 404)
        if principal.has_system_role("R03"):
            return [club_id]
        if principal.leads_club(club_id):
            return [club_id]
        if principal.club_leader_ids:
            raise AppError(40302, "没有该社团的 R02 权限", 403)
        raise AppError(40301, "需要 R03 或目标社团 R02 权限", 403)

    if principal.has_system_role("R03"):
        return None
    if principal.club_leader_ids:
        return sorted(principal.club_leader_ids)
    raise AppError(40301, "需要 R03 或社团 R02 权限", 403)


def require_leader_for_club(principal: Principal, club_id: int) -> None:
    if not principal.leads_club(club_id):
        raise AppError(40302, "没有该社团的 R02 权限", 403)
