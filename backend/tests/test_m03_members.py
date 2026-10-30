import pytest

from app.core.exceptions import AppError
from app.db.models.domain import (
    ClubMember,
    MembershipApplication,
    MembershipType,
    MemberStatus,
)
from app.repositories import club_repository, member_repository
from app.schemas.business import ReviewRequest
from app.schemas.member import (
    ClubMemberUpdateRequest,
    MembershipApplicationCreateRequest,
)
from app.services import member_service
from tests.helpers import (
    make_club,
    make_member,
    make_membership_application,
    make_user,
)


def _patch_club(monkeypatch, club=None):
    club = club or make_club()
    monkeypatch.setattr(club_repository, "get_club", lambda database, club_id, for_update=False: club)
    return club


def test_create_join_application_rejects_active_member(db, student, event_calls, monkeypatch):
    _patch_club(monkeypatch)
    monkeypatch.setattr(
        member_repository,
        "get_membership",
        lambda database, club_id, user_id, for_update=False: make_member(),
    )
    monkeypatch.setattr(member_repository, "get_pending_application", lambda database, club_id, user_id: None)

    with pytest.raises(AppError) as error:
        member_service.create_membership_application(
            db, student, MembershipApplicationCreateRequest(club_id=1, application_type="JOIN")
        )
    assert error.value.code == 40002


def test_create_join_application_rejects_duplicate_pending(db, student, event_calls, monkeypatch):
    _patch_club(monkeypatch)
    monkeypatch.setattr(member_repository, "get_membership", lambda database, club_id, user_id, for_update=False: None)
    monkeypatch.setattr(
        member_repository,
        "get_pending_application",
        lambda database, club_id, user_id: make_membership_application(),
    )

    with pytest.raises(AppError) as error:
        member_service.create_membership_application(
            db, student, MembershipApplicationCreateRequest(club_id=1, application_type="JOIN")
        )
    assert error.value.code == 40902


def test_create_exit_application_requires_active_member(db, student, event_calls, monkeypatch):
    _patch_club(monkeypatch)
    monkeypatch.setattr(
        member_repository,
        "get_membership",
        lambda database, club_id, user_id, for_update=False: make_member(status=MemberStatus.EXITED),
    )
    monkeypatch.setattr(member_repository, "get_pending_application", lambda database, club_id, user_id: None)

    with pytest.raises(AppError) as error:
        member_service.create_membership_application(
            db, student, MembershipApplicationCreateRequest(club_id=1, application_type="EXIT")
        )
    assert error.value.code == 40002


def test_create_join_application_notifies_club_leaders(db, student, event_calls, monkeypatch):
    _patch_club(monkeypatch)
    monkeypatch.setattr(member_repository, "get_membership", lambda database, club_id, user_id, for_update=False: None)
    monkeypatch.setattr(member_repository, "get_pending_application", lambda database, club_id, user_id: None)

    result = member_service.create_membership_application(
        db, student, MembershipApplicationCreateRequest(club_id=1, application_type="JOIN", reason="想加入")
    )

    assert result["status"] == "PENDING"
    assert result["application_type"] == "JOIN"
    assert len(db.objects(MembershipApplication)) == 1
    assert event_calls["notifications"][0][0] == "club_leaders"
    assert event_calls["notifications"][0][1] == 1


def test_process_join_application_creates_member(db, leader, event_calls, monkeypatch):
    application = make_membership_application()
    monkeypatch.setattr(
        member_repository,
        "get_membership_application",
        lambda database, application_id, for_update=False: application,
    )
    monkeypatch.setattr(
        member_repository, "get_membership", lambda database, club_id, user_id, for_update=False: None
    )
    monkeypatch.setattr(member_repository, "get_user", lambda database, user_id: make_user())
    _patch_club(monkeypatch)

    result = member_service.process_membership_application(
        db, leader, application.id, ReviewRequest(decision="APPROVED", comment="欢迎")
    )

    assert result["application"]["status"] == "APPROVED"
    assert result["member"]["status"] == "ACTIVE"
    assert result["member"]["user_id"] == application.applicant_user_id
    members = db.objects(ClubMember)
    assert len(members) == 1
    assert members[0].status == MemberStatus.ACTIVE
    assert event_calls["notifications"][0][0] == "user"


def test_process_exit_application_marks_member_exited(db, leader, event_calls, monkeypatch):
    application = make_membership_application(application_type=MembershipType.EXIT)
    member = make_member()
    monkeypatch.setattr(
        member_repository,
        "get_membership_application",
        lambda database, application_id, for_update=False: application,
    )
    monkeypatch.setattr(
        member_repository,
        "get_membership",
        lambda database, club_id, user_id, for_update=False: member,
    )
    monkeypatch.setattr(member_repository, "get_user", lambda database, user_id: make_user())
    _patch_club(monkeypatch)

    result = member_service.process_membership_application(
        db, leader, application.id, ReviewRequest(decision="APPROVED", comment=None)
    )

    assert result["member"]["status"] == "EXITED"
    assert member.status == MemberStatus.EXITED
    assert member.exited_at is not None


def test_process_application_rejection_keeps_membership_unchanged(
    db, leader, event_calls, monkeypatch
):
    application = make_membership_application()
    monkeypatch.setattr(
        member_repository,
        "get_membership_application",
        lambda database, application_id, for_update=False: application,
    )
    monkeypatch.setattr(member_repository, "get_user", lambda database, user_id: make_user())
    _patch_club(monkeypatch)

    result = member_service.process_membership_application(
        db, leader, application.id, ReviewRequest(decision="REJECTED", comment="暂不接收")
    )

    assert result["application"]["status"] == "REJECTED"
    assert result["member"] is None
    assert db.objects(ClubMember) == []


def test_process_application_blocks_same_person(db, leader, event_calls, monkeypatch):
    application = make_membership_application(applicant_user_id=leader.user_id)
    monkeypatch.setattr(
        member_repository,
        "get_membership_application",
        lambda database, application_id, for_update=False: application,
    )

    with pytest.raises(AppError) as error:
        member_service.process_membership_application(
            db, leader, application.id, ReviewRequest(decision="APPROVED", comment=None)
        )
    assert error.value.code == 40301


def test_withdraw_membership_application_only_pending(db, student, event_calls, monkeypatch):
    application = make_membership_application()
    monkeypatch.setattr(
        member_repository,
        "get_membership_application",
        lambda database, application_id, for_update=False: application,
    )
    _patch_club(monkeypatch)

    result = member_service.withdraw_membership_application(db, student, application.id)
    assert result["status"] == "WITHDRAWN"

    with pytest.raises(AppError) as error:
        member_service.withdraw_membership_application(db, student, application.id)
    assert error.value.code == 40901


def test_member_roster_full_for_leader_and_limited_for_member(
    db, leader, student, event_calls, monkeypatch
):
    _patch_club(monkeypatch)
    member = make_member()
    captured = {}

    def fake_list(database, **kwargs):
        captured.update(kwargs)
        return [(member, "student01", "学生一")], 1

    monkeypatch.setattr(member_repository, "list_club_members", fake_list)

    full = member_service.list_club_members(db, leader, 1, page=1, page_size=20)
    assert full["items"][0]["user_id"] == member.user_id
    assert full["items"][0]["joined_at"] is not None
    assert captured["user_id"] is None

    monkeypatch.setattr(
        member_repository,
        "get_membership",
        lambda database, club_id, user_id, for_update=False: make_member(),
    )
    limited = member_service.list_club_members(db, student, 1, page=1, page_size=20)
    assert limited["items"][0]["user_id"] is None
    assert limited["items"][0]["joined_at"] is None
    assert captured["user_id"] == student.user_id
    assert captured["status"] == MemberStatus.ACTIVE

    monkeypatch.setattr(
        member_repository,
        "get_membership",
        lambda database, club_id, user_id, for_update=False: make_member(status=MemberStatus.EXITED),
    )
    with pytest.raises(AppError) as error:
        member_service.list_club_members(db, student, 1, page=1, page_size=20)
    assert error.value.code == 40302


def test_update_member_position_requires_leader_and_active_member(
    db, student, leader, event_calls, monkeypatch
):
    member = make_member()
    monkeypatch.setattr(
        member_repository,
        "get_member",
        lambda database, club_id, member_id, for_update=False: member,
    )
    monkeypatch.setattr(member_repository, "get_user", lambda database, user_id: make_user())

    with pytest.raises(AppError) as error:
        member_service.update_club_member(
            db, student, 1, member.id, ClubMemberUpdateRequest(position_name="部长")
        )
    assert error.value.code == 40302

    result = member_service.update_club_member(
        db, leader, 1, member.id, ClubMemberUpdateRequest(position_name="部长")
    )
    assert result["position_name"] == "部长"

    member.status = MemberStatus.EXITED
    with pytest.raises(AppError) as error:
        member_service.update_club_member(
            db, leader, 1, member.id, ClubMemberUpdateRequest(position_name="副部长")
        )
    assert error.value.code == 40901


def test_list_membership_applications_scope(db, student, leader, manager, monkeypatch):
    captured = {}

    def fake_list(database, **kwargs):
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(member_repository, "list_membership_applications", fake_list)

    member_service.list_membership_applications(db, student, page=1, page_size=20)
    assert captured["applicant_user_id"] == student.user_id
    assert captured["club_ids"] is None

    member_service.list_membership_applications(db, leader, page=1, page_size=20)
    assert captured["applicant_user_id"] == leader.user_id
    assert captured["club_ids"] == [1]
    assert captured["combine_or"] is True

    member_service.list_membership_applications(db, manager, page=1, page_size=20)
    assert captured["applicant_user_id"] == manager.user_id
    assert captured["club_ids"] is None

    with pytest.raises(AppError) as error:
        member_service.list_membership_applications(
            db, student, page=1, page_size=20, scope="managed"
        )
    assert error.value.code == 40301
