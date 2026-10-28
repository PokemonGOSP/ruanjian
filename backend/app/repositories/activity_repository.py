"""M04 活动与报名的数据访问层（Repository）。"""

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.db.models.domain import (
    AccountStatus,
    Activity,
    ActivityExecutionStatus,
    ActivityRegistration,
    RegistrationStatus,
    ReviewStatus,
    SystemRoleAssignment,
    User,
)


@dataclass(slots=True)
class RegistrationRow:
    """报名记录及其报名人展示信息。"""

    registration: ActivityRegistration
    username: str | None
    display_name: str | None


class ActivityRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, activity_id: int, *, for_update: bool = False) -> Activity | None:
        stmt = select(Activity).where(Activity.id == activity_id)
        if for_update:
            stmt = stmt.with_for_update()
        return self.db.scalar(stmt)

    def add(self, entity: Activity | ActivityRegistration) -> None:
        self.db.add(entity)

    def commit(self) -> None:
        self.db.commit()

    def refresh(self, entity: Activity | ActivityRegistration) -> None:
        self.db.refresh(entity)

    def list_visible(
        self,
        *,
        is_manager: bool,
        leader_club_ids: Iterable[int],
        page: int,
        page_size: int,
    ) -> tuple[list[Activity], int]:
        stmt = select(Activity)
        if not is_manager:
            published = and_(
                Activity.review_status == ReviewStatus.APPROVED,
                Activity.execution_status != ActivityExecutionStatus.UNPUBLISHED,
            )
            club_ids = set(leader_club_ids)
            stmt = stmt.where(or_(Activity.club_id.in_(club_ids), published) if club_ids else published)

        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = self.db.scalars(
            stmt.order_by(Activity.created_at.desc(), Activity.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return list(items), total

    def get_registration(self, activity_id: int, user_id: int) -> ActivityRegistration | None:
        return self.db.scalar(
            select(ActivityRegistration).where(
                ActivityRegistration.activity_id == activity_id,
                ActivityRegistration.user_id == user_id,
            )
        )

    def count_registered(self, activity_id: int) -> int:
        return (
            self.db.scalar(
                select(func.count())
                .select_from(ActivityRegistration)
                .where(
                    ActivityRegistration.activity_id == activity_id,
                    ActivityRegistration.status == RegistrationStatus.REGISTERED,
                )
            )
            or 0
        )

    def registration_counts(self, activity_ids: Iterable[int]) -> dict[int, int]:
        ids = list(activity_ids)
        if not ids:
            return {}
        rows = self.db.execute(
            select(ActivityRegistration.activity_id, func.count())
            .where(
                ActivityRegistration.activity_id.in_(ids),
                ActivityRegistration.status == RegistrationStatus.REGISTERED,
            )
            .group_by(ActivityRegistration.activity_id)
        ).all()
        return {activity_id: count for activity_id, count in rows}

    def registrations_for_user(self, user_id: int, activity_ids: Iterable[int]) -> dict[int, str]:
        ids = list(activity_ids)
        if not ids:
            return {}
        rows = self.db.execute(
            select(ActivityRegistration.activity_id, ActivityRegistration.status).where(
                ActivityRegistration.user_id == user_id,
                ActivityRegistration.activity_id.in_(ids),
            )
        ).all()
        return {activity_id: status.value for activity_id, status in rows}

    def list_registrations(
        self, activity_id: int, *, page: int, page_size: int
    ) -> tuple[list[RegistrationRow], int]:
        total = (
            self.db.scalar(
                select(func.count())
                .select_from(ActivityRegistration)
                .where(ActivityRegistration.activity_id == activity_id)
            )
            or 0
        )
        rows = self.db.execute(
            select(ActivityRegistration, User.username, User.display_name)
            .join(User, User.id == ActivityRegistration.user_id)
            .where(ActivityRegistration.activity_id == activity_id)
            .order_by(ActivityRegistration.registered_at.desc(), ActivityRegistration.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [RegistrationRow(reg, username, display_name) for reg, username, display_name in rows], total

    def registered_user_ids(self, activity_id: int) -> list[int]:
        return list(
            self.db.scalars(
                select(ActivityRegistration.user_id).where(
                    ActivityRegistration.activity_id == activity_id,
                    ActivityRegistration.status == RegistrationStatus.REGISTERED,
                )
            ).all()
        )

    def active_user_ids_with_system_role(self, role_code: str) -> list[int]:
        return list(
            self.db.scalars(
                select(SystemRoleAssignment.user_id)
                .join(User, User.id == SystemRoleAssignment.user_id)
                .where(
                    SystemRoleAssignment.role_code == role_code,
                    SystemRoleAssignment.active.is_(True),
                    User.status == AccountStatus.NORMAL,
                )
            ).all()
        )
