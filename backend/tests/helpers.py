"""测试用 FakeDb 与领域对象工厂（不依赖真实数据库）。"""

from datetime import datetime
from types import SimpleNamespace

from app.db.models.domain import (
    AnnualReviewApplication,
    Club,
    ClubMember,
    ClubRegistrationApplication,
    MembershipApplication,
    MembershipApplicationStatus,
    MembershipType,
    MemberStatus,
    ReviewStatus,
)


class FakeScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return list(self._values)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeDb:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.scalar_result = None
        self.scalars_result = []
        self.rows = []
        self.entities = {}
        self._next_id = 1000

    def add(self, obj):
        self.added.append(obj)
        if getattr(obj, "id", None) is None:
            self._next_id += 1
            obj.id = self._next_id

    def add_all(self, objs):
        for obj in objs:
            self.add(obj)

    def flush(self):
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                self._next_id += 1
                obj.id = self._next_id

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, _obj):
        return None

    def get(self, model, entity_id):
        return self.entities.get((model, entity_id))

    def scalar(self, _statement):
        return self.scalar_result

    def scalars(self, _statement):
        return FakeScalars(self.scalars_result)

    def execute(self, _statement):
        return FakeResult(self.rows)

    def objects(self, model):
        return [obj for obj in self.added if isinstance(obj, model)]


def make_user(user_id=1, username="student01", display_name="学生一"):
    return SimpleNamespace(id=user_id, username=username, display_name=display_name)


def make_registration(    application_id=11,
    applicant_user_id=1,
    status=ReviewStatus.DRAFT,
    name="星河读书社",
):
    application = ClubRegistrationApplication(
        applicant_user_id=applicant_user_id,
        proposed_name=name,
        description="虚构申请",
        advisor_contact="advisor@example.com",
        review_status=status,
    )
    application.id = application_id
    application.created_at = datetime(2026, 1, 1, 9, 0, 0)
    application.submitted_at = datetime(2026, 1, 2, 9, 0, 0) if status != ReviewStatus.DRAFT else None
    application.review_comment = None
    application.reviewed_by = None
    application.reviewed_at = None
    return application


def make_club(club_id=1, name="星河读书社", application_id=11):
    club = Club(
        registration_application_id=application_id,
        name=name,
        description="虚构社团",
        advisor_contact=None,
    )
    club.id = club_id
    club.created_at = datetime(2026, 1, 1, 9, 0, 0)
    club.updated_at = datetime(2026, 1, 1, 9, 0, 0)
    return club


def make_annual_review(
    application_id=21,
    club_id=1,
    year=2026,
    status=ReviewStatus.DRAFT,
    submitted_by=2,
):
    application = AnnualReviewApplication(
        club_id=club_id,
        review_year=year,
        submitted_by=submitted_by,
        materials="虚构年审材料",
        review_status=status,
    )
    application.id = application_id
    application.created_at = datetime(2026, 1, 1, 9, 0, 0)
    application.submitted_at = datetime(2026, 1, 2, 9, 0, 0) if status != ReviewStatus.DRAFT else None
    application.review_comment = None
    application.reviewed_by = None
    application.reviewed_at = None
    return application


def make_member(
    member_id=31,
    club_id=1,
    user_id=1,
    status=MemberStatus.ACTIVE,
    position_name="成员",
):
    member = ClubMember(
        club_id=club_id,
        user_id=user_id,
        position_name=position_name,
        status=status,
    )
    member.id = member_id
    member.joined_at = datetime(2026, 1, 1, 9, 0, 0)
    member.exited_at = datetime(2026, 2, 1, 9, 0, 0) if status == MemberStatus.EXITED else None
    return member


def make_membership_application(
    application_id=41,
    club_id=1,
    applicant_user_id=1,
    application_type=MembershipType.JOIN,
    status=MembershipApplicationStatus.PENDING,
):
    application = MembershipApplication(
        club_id=club_id,
        applicant_user_id=applicant_user_id,
        application_type=application_type,
        reason="虚构理由",
        status=status,
    )
    application.id = application_id
    application.created_at = datetime(2026, 1, 1, 9, 0, 0)
    application.processed_by = None
    application.process_comment = None
    application.processed_at = None
    return application
