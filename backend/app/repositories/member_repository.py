"""M03 数据访问：入团/退出申请、成员关系与社团职务。"""

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.db.models.domain import (
    Club,
    ClubMember,
    MembershipApplication,
    MembershipApplicationStatus,
    MembershipType,
    MemberStatus,
    User,
)


def get_membership_application(
    db: Session, application_id: int, *, for_update: bool = False
) -> MembershipApplication | None:
    statement = select(MembershipApplication).where(MembershipApplication.id == application_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_pending_application(
    db: Session, club_id: int, applicant_user_id: int
) -> MembershipApplication | None:
    return db.scalar(
        select(MembershipApplication).where(
            MembershipApplication.club_id == club_id,
            MembershipApplication.applicant_user_id == applicant_user_id,
            MembershipApplication.status == MembershipApplicationStatus.PENDING,
        )
    )


def list_membership_applications(
    db: Session,
    *,
    applicant_user_id: int | None = None,
    club_ids: Sequence[int] | None = None,
    combine_or: bool = False,
    club_id: int | None = None,
    status: MembershipApplicationStatus | None = None,
    application_type: MembershipType | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[MembershipApplication, str, str, str | None]], int]:
    filters = []
    if club_id is not None:
        filters.append(MembershipApplication.club_id == club_id)
    if status is not None:
        filters.append(MembershipApplication.status == status)
    if application_type is not None:
        filters.append(MembershipApplication.application_type == application_type)

    if combine_or and applicant_user_id is not None and club_ids:
        filters.append(
            or_(
                MembershipApplication.applicant_user_id == applicant_user_id,
                MembershipApplication.club_id.in_(list(club_ids)),
            )
        )
    elif applicant_user_id is not None:
        filters.append(MembershipApplication.applicant_user_id == applicant_user_id)
    elif club_ids is not None:
        if not club_ids:
            return [], 0
        filters.append(MembershipApplication.club_id.in_(list(club_ids)))

    total = db.scalar(select(func.count()).select_from(MembershipApplication).where(*filters)) or 0
    applicant = aliased(User)
    processor = aliased(User)
    statement = (
        select(MembershipApplication, Club.name, applicant.display_name, processor.display_name)
        .join(Club, Club.id == MembershipApplication.club_id)
        .join(applicant, applicant.id == MembershipApplication.applicant_user_id)
        .outerjoin(processor, processor.id == MembershipApplication.processed_by)
        .where(*filters)
        .order_by(MembershipApplication.created_at.desc(), MembershipApplication.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(statement).all()
    return [(row[0], row[1], row[2], row[3]) for row in rows], int(total)


def get_membership(db: Session, club_id: int, user_id: int, *, for_update: bool = False) -> ClubMember | None:
    statement = select(ClubMember).where(ClubMember.club_id == club_id, ClubMember.user_id == user_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_member(db: Session, club_id: int, member_id: int, *, for_update: bool = False) -> ClubMember | None:
    statement = select(ClubMember).where(ClubMember.club_id == club_id, ClubMember.id == member_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def list_club_members(
    db: Session,
    *,
    club_id: int,
    user_id: int | None = None,
    status: MemberStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[ClubMember, str, str]], int]:
    filters = [ClubMember.club_id == club_id]
    if user_id is not None:
        filters.append(ClubMember.user_id == user_id)
    if status is not None:
        filters.append(ClubMember.status == status)

    total = db.scalar(select(func.count()).select_from(ClubMember).where(*filters)) or 0
    statement = (
        select(ClubMember, User.username, User.display_name)
        .join(User, User.id == ClubMember.user_id)
        .where(*filters)
        .order_by(ClubMember.status.asc(), ClubMember.id.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(statement).all()
    return [(row[0], row[1], row[2]) for row in rows], int(total)


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def distinct_active_member_count(db: Session, club_ids: Sequence[int] | None = None) -> int:
    filters = [ClubMember.status == MemberStatus.ACTIVE]
    if club_ids is not None:
        if not club_ids:
            return 0
        filters.append(ClubMember.club_id.in_(list(club_ids)))
    return int(db.scalar(select(func.count(func.distinct(ClubMember.user_id))).where(*filters)) or 0)


def member_counts_by_club(db: Session, club_ids: Sequence[int] | None = None) -> dict[int, dict[str, int]]:
    """按社团汇总成员关系；返回 {club_id: {ACTIVE: n, EXITED: n}}。"""
    filters = []
    if club_ids is not None:
        if not club_ids:
            return {}
        filters.append(ClubMember.club_id.in_(list(club_ids)))
    rows = db.execute(
        select(ClubMember.club_id, ClubMember.status, func.count(ClubMember.id))
        .where(*filters)
        .group_by(ClubMember.club_id, ClubMember.status)
    ).all()
    result: dict[int, dict[str, int]] = {}
    for club_id, member_status, count in rows:
        bucket = result.setdefault(int(club_id), {"ACTIVE": 0, "EXITED": 0})
        key = member_status.value if hasattr(member_status, "value") else str(member_status)
        bucket[key] = int(count)
    return result


def pending_application_counts_by_club(
    db: Session, club_ids: Sequence[int] | None = None
) -> dict[int, int]:
    filters = [MembershipApplication.status == MembershipApplicationStatus.PENDING]
    if club_ids is not None:
        if not club_ids:
            return {}
        filters.append(MembershipApplication.club_id.in_(list(club_ids)))
    rows = db.execute(
        select(MembershipApplication.club_id, func.count(MembershipApplication.id))
        .where(*filters)
        .group_by(MembershipApplication.club_id)
    ).all()
    return {int(club_id): int(count) for club_id, count in rows}
