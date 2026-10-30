"""M02 数据访问：社团注册申请、社团资料与年审申请。

Repository 只负责查询/持久化，不判断权限或状态；业务规则集中在 Service。
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.domain import (
    AnnualReviewApplication,
    Club,
    ClubRegistrationApplication,
    ReviewStatus,
    User,
)


def get_registration_application(
    db: Session, application_id: int, *, for_update: bool = False
) -> ClubRegistrationApplication | None:
    statement = select(ClubRegistrationApplication).where(ClubRegistrationApplication.id == application_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def list_registration_applications(
    db: Session,
    *,
    applicant_user_id: int | None = None,
    review_status: ReviewStatus | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[ClubRegistrationApplication, str]], int]:
    filters = []
    if applicant_user_id is not None:
        filters.append(ClubRegistrationApplication.applicant_user_id == applicant_user_id)
    if review_status is not None:
        filters.append(ClubRegistrationApplication.review_status == review_status)

    total = db.scalar(select(func.count()).select_from(ClubRegistrationApplication).where(*filters)) or 0
    statement = (
        select(ClubRegistrationApplication, User.display_name)
        .join(User, User.id == ClubRegistrationApplication.applicant_user_id)
        .where(*filters)
        .order_by(ClubRegistrationApplication.created_at.desc(), ClubRegistrationApplication.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(statement).all()
    return [(row[0], row[1]) for row in rows], int(total)


def get_club(db: Session, club_id: int, *, for_update: bool = False) -> Club | None:
    statement = select(Club).where(Club.id == club_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_club_by_name(db: Session, name: str) -> Club | None:
    return db.scalar(select(Club).where(Club.name == name))


def get_club_by_registration_application(db: Session, application_id: int) -> Club | None:
    return db.scalar(select(Club).where(Club.registration_application_id == application_id))


def list_clubs(db: Session, *, page: int = 1, page_size: int = 20) -> tuple[list[Club], int]:
    total = db.scalar(select(func.count()).select_from(Club)) or 0
    statement = (
        select(Club)
        .order_by(Club.created_at.desc(), Club.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(statement).all()), int(total)


def all_clubs(db: Session, club_ids: Sequence[int] | None = None) -> list[Club]:
    statement = select(Club)
    if club_ids is not None:
        if not club_ids:
            return []
        statement = statement.where(Club.id.in_(list(club_ids)))
    return list(db.scalars(statement.order_by(Club.name.asc(), Club.id.asc())).all())


def get_annual_review(db: Session, application_id: int, *, for_update: bool = False) -> AnnualReviewApplication | None:
    statement = select(AnnualReviewApplication).where(AnnualReviewApplication.id == application_id)
    if for_update:
        statement = statement.with_for_update()
    return db.scalar(statement)


def get_annual_review_by_club_year(
    db: Session, club_id: int, review_year: int
) -> AnnualReviewApplication | None:
    return db.scalar(
        select(AnnualReviewApplication).where(
            AnnualReviewApplication.club_id == club_id,
            AnnualReviewApplication.review_year == review_year,
        )
    )


def annual_review_status_by_year(
    db: Session, club_ids: Sequence[int], review_year: int
) -> dict[int, ReviewStatus]:
    if not club_ids:
        return {}
    rows = db.execute(
        select(AnnualReviewApplication.club_id, AnnualReviewApplication.review_status).where(
            AnnualReviewApplication.club_id.in_(list(club_ids)),
            AnnualReviewApplication.review_year == review_year,
        )
    ).all()
    return {int(club_id): status for club_id, status in rows}


def list_annual_reviews(    db: Session,
    *,
    club_ids: Sequence[int] | None = None,
    review_status: ReviewStatus | None = None,
    review_year: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[tuple[AnnualReviewApplication, str, str]], int]:
    filters = []
    if club_ids is not None:
        if not club_ids:
            return [], 0
        filters.append(AnnualReviewApplication.club_id.in_(list(club_ids)))
    if review_status is not None:
        filters.append(AnnualReviewApplication.review_status == review_status)
    if review_year is not None:
        filters.append(AnnualReviewApplication.review_year == review_year)

    total = db.scalar(select(func.count()).select_from(AnnualReviewApplication).where(*filters)) or 0
    statement = (
        select(AnnualReviewApplication, Club.name, User.display_name)
        .join(Club, Club.id == AnnualReviewApplication.club_id)
        .join(User, User.id == AnnualReviewApplication.submitted_by)
        .where(*filters)
        .order_by(
            AnnualReviewApplication.review_year.desc(),
            AnnualReviewApplication.created_at.desc(),
            AnnualReviewApplication.id.desc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = db.execute(statement).all()
    return [(row[0], row[1], row[2]) for row in rows], int(total)
