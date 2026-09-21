from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models.domain import (
    AccountStatus,
    Activity,
    ActivityExecutionStatus,
    ActivityRegistration,
    AnnualReviewApplication,
    Club,
    ClubMember,
    ClubRegistrationApplication,
    ClubRoleAssignment,
    FinanceRecord,
    FinanceType,
    MemberStatus,
    Notification,
    ReadStatus,
    RecordStatus,
    RegistrationStatus,
    ReviewStatus,
    SystemRoleAssignment,
    User,
)
from app.db.session import SessionLocal


USERS = [
    ("student01", "Student123!", "学生一"),
    ("student02", "Student123!", "学生二"),
    ("leader01", "Leader123!", "社团负责人一"),
    ("leader02", "Leader123!", "社团负责人二"),
    ("manager01", "Manager123!", "社团管理人员"),
    ("admin01", "Admin123!", "系统管理员"),
]


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Seed skipped: users table is not empty.")
            return

        users = {username: User(username=username, password_hash=hash_password(password), display_name=name, status=AccountStatus.NORMAL) for username, password, name in USERS}
        db.add_all(users.values())
        db.flush()
        db.add_all([
            SystemRoleAssignment(user_id=user.id, role_code="R01", active=True)
            for user in users.values()
        ] + [
            SystemRoleAssignment(user_id=users["manager01"].id, role_code="R03", active=True, granted_by=users["admin01"].id),
            SystemRoleAssignment(user_id=users["admin01"].id, role_code="R04", active=True, granted_by=users["admin01"].id),
        ])

        approved_apps = []
        for name, applicant in [("星河读书社", "leader01"), ("像素创意社", "leader02"), ("晨风运动社", "leader01")]:
            item = ClubRegistrationApplication(applicant_user_id=users[applicant].id, proposed_name=name, description=f"虚构测试社团：{name}", review_status=ReviewStatus.APPROVED, review_comment="Seed approval", reviewed_by=users["manager01"].id, submitted_at=datetime.now(), reviewed_at=datetime.now())
            db.add(item)
            approved_apps.append((item, applicant))
        db.add_all([
            ClubRegistrationApplication(applicant_user_id=users["student01"].id, proposed_name="纸飞机兴趣社", description="草稿测试", review_status=ReviewStatus.DRAFT),
            ClubRegistrationApplication(applicant_user_id=users["student01"].id, proposed_name="逻辑谜题社", description="待审核测试", review_status=ReviewStatus.PENDING, submitted_at=datetime.now()),
            ClubRegistrationApplication(applicant_user_id=users["student02"].id, proposed_name="远山摄影社", description="驳回测试", review_status=ReviewStatus.REJECTED, review_comment="测试材料不完整", reviewed_by=users["manager01"].id, submitted_at=datetime.now(), reviewed_at=datetime.now()),
        ])
        db.flush()
        clubs = []
        for app, applicant in approved_apps:
            club = Club(registration_application_id=app.id, name=app.proposed_name, description=app.description)
            db.add(club)
            clubs.append((club, applicant))
        db.flush()
        for club, applicant in clubs:
            db.add(ClubRoleAssignment(user_id=users[applicant].id, club_id=club.id, role_code="R02", active=True, granted_by=users["manager01"].id))
            db.add(ClubMember(club_id=club.id, user_id=users[applicant].id, position_name="负责人", status=MemberStatus.ACTIVE))
        db.add(ClubMember(club_id=clubs[0][0].id, user_id=users["student01"].id, position_name="成员", status=MemberStatus.ACTIVE))

        for index, status in enumerate([ReviewStatus.DRAFT, ReviewStatus.PENDING, ReviewStatus.APPROVED, ReviewStatus.REJECTED], start=1):
            db.add(AnnualReviewApplication(club_id=clubs[0][0].id, review_year=2022 + index, submitted_by=users["leader01"].id, materials=f"年审测试材料 {index}", review_status=status, review_comment="Seed review" if status in {ReviewStatus.APPROVED, ReviewStatus.REJECTED} else None))

        now = datetime.now()
        activity_states = [
            ("未发布读书会", ReviewStatus.APPROVED, ActivityExecutionStatus.UNPUBLISHED),
            ("开放报名创意展", ReviewStatus.APPROVED, ActivityExecutionStatus.REGISTRATION_OPEN),
            ("已结束分享会", ReviewStatus.APPROVED, ActivityExecutionStatus.ENDED),
            ("已取消晨跑", ReviewStatus.APPROVED, ActivityExecutionStatus.CANCELLED),
            ("活动草稿", ReviewStatus.DRAFT, ActivityExecutionStatus.UNPUBLISHED),
            ("待审核活动", ReviewStatus.PENDING, ActivityExecutionStatus.UNPUBLISHED),
            ("已驳回活动", ReviewStatus.REJECTED, ActivityExecutionStatus.UNPUBLISHED),
        ]
        activities = []
        for index, (title, review, execution) in enumerate(activity_states):
            activity = Activity(club_id=clubs[index % 3][0].id, created_by=users[clubs[index % 3][1]].id, title=title, description="虚构 Seed 活动", location="测试场地", starts_at=now + timedelta(days=index + 1), ends_at=now + timedelta(days=index + 1, hours=2), registration_deadline=now + timedelta(days=index), capacity=30, budget=Decimal("100.00"), review_status=review, execution_status=execution, cancellation_reason="Seed cancellation" if execution == ActivityExecutionStatus.CANCELLED else None)
            db.add(activity)
            activities.append(activity)
        db.flush()
        db.add(ActivityRegistration(activity_id=activities[1].id, user_id=users["student01"].id, status=RegistrationStatus.REGISTERED))

        db.add_all([
            FinanceRecord(club_id=clubs[0][0].id, record_type=FinanceType.INCOME, amount=Decimal("500.00"), occurred_on=now, description="虚构会费收入", status=RecordStatus.ACTIVE, created_by=users["leader01"].id),
            FinanceRecord(club_id=clubs[0][0].id, activity_id=activities[0].id, record_type=FinanceType.EXPENSE, amount=Decimal("88.00"), occurred_on=now, description="虚构活动材料支出", status=RecordStatus.ACTIVE, created_by=users["leader01"].id),
            FinanceRecord(club_id=clubs[1][0].id, record_type=FinanceType.EXPENSE, amount=Decimal("20.00"), occurred_on=now, description="虚构作废记录", status=RecordStatus.VOIDED, created_by=users["leader02"].id, voided_by=users["leader02"].id, void_reason="Seed void"),
            Notification(recipient_user_id=users["student01"].id, title="报名成功", content="虚构通知：活动报名成功", event_type="ACTIVITY_REGISTRATION", read_status=ReadStatus.UNREAD),
            Notification(recipient_user_id=users["leader01"].id, title="审核结果", content="虚构通知：申请已通过", event_type="REVIEW_RESULT", read_status=ReadStatus.READ, read_at=now),
        ])
        db.commit()
        print("Seed completed: 6 users, 3 clubs, applications, activities, finance records and notifications.")


if __name__ == "__main__":
    seed()
