"""M04 活动管理服务层。

覆盖 FR-11～FR-16：活动申请创建/编辑/提交/撤回、R03 审核、发布、报名/取消报名、
执行阶段取消与结束归档。审核状态（ReviewStatus）与执行状态（ActivityExecutionStatus）
严格分离；状态转换、资源归属和事务提交集中在本层。
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Protocol

from app.core.exceptions import AppError
from app.core.permissions import Principal, require_club_leader, require_system_role
from app.db.models.domain import (
    Activity,
    ActivityExecutionStatus,
    ActivityRegistration,
    RegistrationStatus,
    ReviewStatus,
)
from app.repositories.activity_repository import ActivityRepository, RegistrationRow
from app.schemas.activity import ActivityData, RegistrationData, RegistrationUserData
from app.schemas.business import (
    ActivityCreateRequest,
    ActivityEndRequest,
    ActivityUpdateRequest,
    ReviewRequest,
)
from app.services.notification_service import NotificationService

EDITABLE_REVIEW_STATUSES = (ReviewStatus.DRAFT, ReviewStatus.WITHDRAWN)
ENDABLE_EXECUTION_STATUSES = (
    ActivityExecutionStatus.REGISTRATION_CLOSED,
    ActivityExecutionStatus.IN_PROGRESS,
)
CANCELLABLE_EXECUTION_STATUSES = (
    ActivityExecutionStatus.UNPUBLISHED,
    ActivityExecutionStatus.REGISTRATION_OPEN,
    ActivityExecutionStatus.REGISTRATION_CLOSED,
    ActivityExecutionStatus.IN_PROGRESS,
)


class Notifier(Protocol):
    def notify_users(
        self,
        user_ids: Iterable[int],
        *,
        title: str,
        content: str,
        event_type: str,
        related_id: int | None = None,
    ) -> int: ...


def _naive(value: datetime) -> datetime:
    """数据库 DATETIME 不保存时区；带时区输入统一转成本地时间后去掉 tzinfo。"""

    if value.tzinfo is None:
        return value
    return value.astimezone().replace(tzinfo=None)


class ActivityService:
    def __init__(
        self,
        db=None,
        *,
        repo: ActivityRepository | None = None,
        notifier: Notifier | None = None,
        now: Callable[[], datetime] | None = None,
    ):
        self.db = db
        self.repo = repo or ActivityRepository(db)
        self.notifier = notifier or NotificationService(db)
        self._now = now or datetime.now

    # ------------------------------------------------------------------
    # 公共工具
    # ------------------------------------------------------------------
    def now(self) -> datetime:
        return self._now()

    def _require_activity(self, activity_id: int, *, for_update: bool = True) -> Activity:
        activity = self.repo.get(activity_id, for_update=for_update)
        if activity is None:
            raise AppError(40401, "活动不存在", 404)
        return activity

    @staticmethod
    def _validate_schedule(
        starts_at: datetime, ends_at: datetime, registration_deadline: datetime | None
    ) -> None:
        if starts_at >= ends_at:
            raise AppError(40002, "活动开始时间必须早于结束时间", 400)
        if registration_deadline is not None and registration_deadline >= starts_at:
            raise AppError(40002, "报名截止时间必须早于活动开始时间", 400)

    def _sync_execution_status(self, activity: Activity) -> bool:
        """按时间推进系统状态：报名截止 → 报名截止；开始时间到达 → 进行中。

        活动结束仍由 R02 通过 FR-16 显式归档，以便填写活动总结。
        """
        if activity.review_status != ReviewStatus.APPROVED:
            return False

        now = self.now()
        changed = False
        # 最多两步：报名中 → 报名截止 → 进行中。
        for _ in range(3):
            if (
                activity.execution_status == ActivityExecutionStatus.REGISTRATION_OPEN
                and activity.registration_deadline is not None
                and now >= activity.registration_deadline
            ):
                activity.execution_status = ActivityExecutionStatus.REGISTRATION_CLOSED
                activity.updated_at = now
                changed = True
                continue
            if (
                activity.execution_status
                in (ActivityExecutionStatus.REGISTRATION_OPEN, ActivityExecutionStatus.REGISTRATION_CLOSED)
                and now >= activity.starts_at
            ):
                activity.execution_status = ActivityExecutionStatus.IN_PROGRESS
                activity.updated_at = now
                changed = True
                continue
            break
        return changed

    def _can_view_full(self, principal: Principal, activity: Activity) -> bool:
        return principal.has_system_role("R03") or principal.leads_club(activity.club_id)

    def _assert_can_view(self, principal: Principal, activity: Activity) -> None:
        if self._can_view_full(principal, activity):
            return
        if (
            activity.review_status != ReviewStatus.APPROVED
            or activity.execution_status == ActivityExecutionStatus.UNPUBLISHED
        ):
            raise AppError(40301, "无权查看该活动", 403)

    def activity_data(
        self,
        activity: Activity,
        *,
        registration_count: int,
        my_registration_status: str | None,
    ) -> dict:
        data = ActivityData(
            id=activity.id,
            club_id=activity.club_id,
            created_by=activity.created_by,
            title=activity.title,
            description=activity.description,
            location=activity.location,
            starts_at=activity.starts_at,
            ends_at=activity.ends_at,
            registration_deadline=activity.registration_deadline,
            capacity=activity.capacity,
            budget=float(activity.budget or 0),
            review_status=activity.review_status.value,
            execution_status=activity.execution_status.value,
            review_comment=activity.review_comment,
            reviewed_by=activity.reviewed_by,
            cancellation_reason=activity.cancellation_reason,
            summary=activity.summary,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
            registration_count=registration_count,
            my_registration_status=my_registration_status,
        )
        return data.model_dump()

    def _single_data(self, principal: Principal, activity: Activity) -> dict:
        return self.activity_data(
            activity,
            registration_count=self.repo.count_registered(activity.id),
            my_registration_status=self.repo.registrations_for_user(
                principal.user_id, [activity.id]
            ).get(activity.id),
        )

    @staticmethod
    def registration_data(row: RegistrationRow) -> dict:
        registration = row.registration
        user = None
        if row.username is not None:
            user = RegistrationUserData(
                id=registration.user_id,
                username=row.username,
                display_name=row.display_name or row.username,
            ).model_dump()
        data = RegistrationData(
            id=registration.id,
            activity_id=registration.activity_id,
            user_id=registration.user_id,
            status=registration.status.value,
            registered_at=registration.registered_at,
            cancelled_at=registration.cancelled_at,
            user=user,
        )
        return data.model_dump()

    def _notify(
        self,
        user_ids: Iterable[int],
        *,
        title: str,
        content: str,
        event_type: str,
        related_id: int | None,
    ) -> None:
        self.notifier.notify_users(
            user_ids,
            title=title,
            content=content,
            event_type=event_type,
            related_id=related_id,
        )

    # ------------------------------------------------------------------
    # FR-11 创建 / 编辑
    # ------------------------------------------------------------------
    def create(self, principal: Principal, body: ActivityCreateRequest) -> dict:
        require_club_leader(principal, body.club_id)
        title = body.title.strip()
        description = body.description.strip()
        location = body.location.strip()
        if not title or not description or not location:
            raise AppError(40001, "活动名称、方案说明和地点不能为空", 422)

        starts_at = _naive(body.starts_at)
        ends_at = _naive(body.ends_at)
        deadline = _naive(body.registration_deadline) if body.registration_deadline else None
        self._validate_schedule(starts_at, ends_at, deadline)

        now = self.now()
        activity = Activity(
            club_id=body.club_id,
            created_by=principal.user_id,
            title=title,
            description=description,
            location=location,
            starts_at=starts_at,
            ends_at=ends_at,
            registration_deadline=deadline,
            capacity=body.capacity,
            budget=body.budget,
            review_status=ReviewStatus.DRAFT,
            execution_status=ActivityExecutionStatus.UNPUBLISHED,
            created_at=now,
            updated_at=now,
        )
        self.repo.add(activity)
        self.repo.commit()
        self.repo.refresh(activity)
        return self.activity_data(activity, registration_count=0, my_registration_status=None)

    def update(
        self, principal: Principal, activity_id: int, body: ActivityUpdateRequest
    ) -> dict:
        activity = self._require_activity(activity_id)
        require_club_leader(principal, activity.club_id)
        if activity.review_status not in EDITABLE_REVIEW_STATUSES:
            raise AppError(40901, "当前审核状态不允许编辑", 409)

        updates = body.model_dump(exclude_unset=True)
        for field in ("title", "description", "location", "starts_at", "ends_at", "budget"):
            if field in updates and updates[field] is None:
                raise AppError(40002, f"{field} 不能为空", 400)
        for field in ("title", "description", "location"):
            if field in updates:
                updates[field] = updates[field].strip()
                if not updates[field]:
                    raise AppError(40001, "活动名称、方案说明和地点不能为空", 422)
        for field in ("starts_at", "ends_at", "registration_deadline"):
            if field in updates and updates[field] is not None:
                updates[field] = _naive(updates[field])

        starts_at = updates.get("starts_at", activity.starts_at)
        ends_at = updates.get("ends_at", activity.ends_at)
        deadline = updates.get("registration_deadline", activity.registration_deadline)
        self._validate_schedule(starts_at, ends_at, deadline)

        for field, value in updates.items():
            setattr(activity, field, value)
        activity.updated_at = self.now()
        self.repo.commit()
        self.repo.refresh(activity)
        return self._single_data(principal, activity)

    # ------------------------------------------------------------------
    # FR-12 提交 / 撤回
    # ------------------------------------------------------------------
    def submit(self, principal: Principal, activity_id: int) -> dict:
        activity = self._require_activity(activity_id)
        require_club_leader(principal, activity.club_id)
        if activity.review_status not in EDITABLE_REVIEW_STATUSES:
            raise AppError(40901, "当前状态不允许提交审核", 409)
        if activity.ends_at <= self.now():
            raise AppError(40002, "活动结束时间已过，不能提交审核", 400)

        activity.review_status = ReviewStatus.PENDING
        activity.review_comment = None
        activity.reviewed_by = None
        activity.updated_at = self.now()
        self._notify(
            self.repo.active_user_ids_with_system_role("R03"),
            title="活动申请待审核",
            content=f"社团活动《{activity.title}》已提交审核，请及时处理。",
            event_type="ACTIVITY_SUBMITTED",
            related_id=activity.id,
        )
        self.repo.commit()
        self.repo.refresh(activity)
        return self._single_data(principal, activity)

    def withdraw(self, principal: Principal, activity_id: int) -> dict:
        activity = self._require_activity(activity_id)
        require_club_leader(principal, activity.club_id)
        if activity.review_status != ReviewStatus.PENDING:
            raise AppError(40901, "当前状态不允许撤回", 409)
        activity.review_status = ReviewStatus.WITHDRAWN
        activity.updated_at = self.now()
        self.repo.commit()
        self.repo.refresh(activity)
        return self._single_data(principal, activity)

    # ------------------------------------------------------------------
    # FR-13 审核
    # ------------------------------------------------------------------
    def review(self, principal: Principal, activity_id: int, body: ReviewRequest) -> dict:
        require_system_role(principal, "R03")
        activity = self._require_activity(activity_id)
        if activity.review_status != ReviewStatus.PENDING:
            raise AppError(40901, "当前状态不允许审核", 409)

        approved = body.decision == "APPROVED"
        activity.review_status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
        activity.review_comment = body.comment
        activity.reviewed_by = principal.user_id
        # 只有审核通过后活动才进入执行阶段；驳回保持未发布。
        if approved:
            activity.execution_status = ActivityExecutionStatus.UNPUBLISHED
        activity.updated_at = self.now()

        result = "通过" if approved else "驳回"
        comment = f" 审核意见：{body.comment}" if body.comment else ""
        self._notify(
            [activity.created_by],
            title="活动审核结果",
            content=f"活动《{activity.title}》审核{result}。{comment}",
            event_type="ACTIVITY_REVIEWED",
            related_id=activity.id,
        )
        self.repo.commit()
        self.repo.refresh(activity)
        return self._single_data(principal, activity)

    # ------------------------------------------------------------------
    # FR-14 发布 / 查询
    # ------------------------------------------------------------------
    def publish(self, principal: Principal, activity_id: int) -> dict:
        activity = self._require_activity(activity_id)
        require_club_leader(principal, activity.club_id)
        if activity.review_status != ReviewStatus.APPROVED:
            raise AppError(40901, "活动尚未审核通过", 409)
        if activity.execution_status != ActivityExecutionStatus.UNPUBLISHED:
            raise AppError(40901, "当前执行状态不允许发布", 409)
        now = self.now()
        if now >= activity.starts_at:
            raise AppError(40901, "活动已开始，不能发布", 409)
        if activity.registration_deadline is not None and now >= activity.registration_deadline:
            raise AppError(40901, "报名截止时间已过，不能发布", 409)

        activity.execution_status = ActivityExecutionStatus.REGISTRATION_OPEN
        activity.updated_at = now
        self.repo.commit()
        self.repo.refresh(activity)
        return self._single_data(principal, activity)

    def list(self, principal: Principal, *, page: int, page_size: int) -> tuple[list[dict], int]:
        items, total = self.repo.list_visible(
            is_manager=principal.has_system_role("R03"),
            leader_club_ids=principal.club_leader_ids,
            page=page,
            page_size=page_size,
        )
        changed = False
        for activity in items:
            changed = self._sync_execution_status(activity) or changed
        if changed:
            self.repo.commit()

        ids = [activity.id for activity in items]
        counts = self.repo.registration_counts(ids)
        mine = self.repo.registrations_for_user(principal.user_id, ids)
        return [
            self.activity_data(
                activity,
                registration_count=counts.get(activity.id, 0),
                my_registration_status=mine.get(activity.id),
            )
            for activity in items
        ], total

    def get(self, principal: Principal, activity_id: int) -> dict:
        activity = self._require_activity(activity_id, for_update=False)
        self._assert_can_view(principal, activity)
        if self._sync_execution_status(activity):
            self.repo.commit()
        return self._single_data(principal, activity)

    # ------------------------------------------------------------------
    # FR-15 报名 / 取消报名 / 报名名单
    # ------------------------------------------------------------------
    def register(self, principal: Principal, activity_id: int) -> dict:
        activity = self._require_activity(activity_id)
        changed = self._sync_execution_status(activity)
        if activity.review_status != ReviewStatus.APPROVED:
            raise AppError(40901, "活动尚未审核通过，不能报名", 409)
        if activity.execution_status != ActivityExecutionStatus.REGISTRATION_OPEN:
            raise AppError(40901, "活动当前不接受报名", 409)

        now = self.now()
        if activity.registration_deadline is not None and now >= activity.registration_deadline:
            raise AppError(40901, "报名已截止", 409)

        registration = self.repo.get_registration(activity.id, principal.user_id)
        if registration is not None and registration.status == RegistrationStatus.REGISTERED:
            raise AppError(40902, "已报名，不可重复报名", 409)
        if (
            activity.capacity is not None
            and self.repo.count_registered(activity.id) >= activity.capacity
        ):
            raise AppError(40901, "报名人数已满", 409)

        if registration is None:
            registration = ActivityRegistration(
                activity_id=activity.id,
                user_id=principal.user_id,
                status=RegistrationStatus.REGISTERED,
                registered_at=now,
            )
            self.repo.add(registration)
        else:
            registration.status = RegistrationStatus.REGISTERED
            registration.registered_at = now
            registration.cancelled_at = None

        self._notify(
            [principal.user_id],
            title="报名成功",
            content=f"您已成功报名活动《{activity.title}》。",
            event_type="ACTIVITY_REGISTRATION",
            related_id=activity.id,
        )
        if activity.created_by != principal.user_id:
            self._notify(
                [activity.created_by],
                title="活动有新报名",
                content=f"{principal.display_name} 报名了活动《{activity.title}》。",
                event_type="ACTIVITY_REGISTRATION_RECEIVED",
                related_id=activity.id,
            )

        if changed:
            activity.updated_at = now
        self.repo.commit()
        self.repo.refresh(registration)
        return self.registration_data(
            RegistrationRow(registration, principal.username, principal.display_name)
        )

    def cancel_registration(self, principal: Principal, activity_id: int) -> dict:
        activity = self._require_activity(activity_id)
        changed = self._sync_execution_status(activity)
        registration = self.repo.get_registration(activity.id, principal.user_id)
        if registration is None:
            raise AppError(40401, "未找到报名记录", 404)
        if registration.status != RegistrationStatus.REGISTERED:
            raise AppError(40901, "报名已取消", 409)
        if activity.execution_status in (
            ActivityExecutionStatus.ENDED,
            ActivityExecutionStatus.CANCELLED,
        ):
            raise AppError(40901, "活动已结束或已取消，不能取消报名", 409)

        now = self.now()
        registration.status = RegistrationStatus.CANCELLED
        registration.cancelled_at = now
        if activity.created_by != principal.user_id:
            self._notify(
                [activity.created_by],
                title="有学生取消报名",
                content=f"{principal.display_name} 取消了活动《{activity.title}》的报名。",
                event_type="ACTIVITY_REGISTRATION_CANCELLED",
                related_id=activity.id,
            )
        if changed:
            activity.updated_at = now
        self.repo.commit()
        return {}

    def list_registrations(
        self, principal: Principal, activity_id: int, *, page: int, page_size: int
    ) -> tuple[list[dict], int]:
        activity = self._require_activity(activity_id, for_update=False)
        require_club_leader(principal, activity.club_id)
        rows, total = self.repo.list_registrations(activity_id, page=page, page_size=page_size)
        return [self.registration_data(row) for row in rows], total

    # ------------------------------------------------------------------
    # FR-16 取消 / 结束
    # ------------------------------------------------------------------
    def cancel(self, principal: Principal, activity_id: int, reason: str) -> dict:
        activity = self._require_activity(activity_id)
        require_club_leader(principal, activity.club_id)
        if activity.review_status != ReviewStatus.APPROVED:
            raise AppError(40901, "活动尚未审核通过，不能取消", 409)
        if activity.execution_status in (
            ActivityExecutionStatus.ENDED,
            ActivityExecutionStatus.CANCELLED,
        ):
            raise AppError(40901, "已结束或已取消的活动不能再次取消", 409)

        cleaned_reason = reason.strip()
        if not cleaned_reason:
            raise AppError(40002, "取消原因不能为空", 400)

        now = self.now()
        activity.execution_status = ActivityExecutionStatus.CANCELLED
        activity.cancellation_reason = cleaned_reason
        activity.updated_at = now

        participants = self.repo.registered_user_ids(activity.id)
        self._notify(
            participants,
            title="活动已取消",
            content=f"您报名的活动《{activity.title}》已取消。取消原因：{cleaned_reason}",
            event_type="ACTIVITY_CANCELLED",
            related_id=activity.id,
        )
        self.repo.commit()
        self.repo.refresh(activity)
        return self._single_data(principal, activity)

    def end(
        self, principal: Principal, activity_id: int, body: ActivityEndRequest
    ) -> dict:
        activity = self._require_activity(activity_id)
        require_club_leader(principal, activity.club_id)
        if activity.review_status != ReviewStatus.APPROVED:
            raise AppError(40901, "活动尚未审核通过，不能结束", 409)

        self._sync_execution_status(activity)
        if activity.execution_status not in ENDABLE_EXECUTION_STATUSES:
            raise AppError(40901, "当前执行状态不允许结束", 409)

        activity.execution_status = ActivityExecutionStatus.ENDED
        if body.summary is not None and body.summary.strip():
            activity.summary = body.summary.strip()
        activity.updated_at = self.now()
        self.repo.commit()
        self.repo.refresh(activity)
        return self._single_data(principal, activity)
