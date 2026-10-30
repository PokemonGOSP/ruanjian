import pytest

from app.core.exceptions import AppError
from app.db.models.domain import (
    Club,
    ClubMember,
    ClubRegistrationApplication,
    ClubRoleAssignment,
    ReviewStatus,
)
from app.main import app
from app.repositories import club_repository
from app.schemas.business import ReviewRequest
from app.schemas.club import (
    ClubRegistrationCreateRequest,
    ClubRegistrationUpdateRequest,
    ClubUpdateRequest,
)
from app.services import club_service
from tests.helpers import make_club, make_registration


def test_create_registration_starts_as_draft(db, student, event_calls):
    body = ClubRegistrationCreateRequest(
        proposed_name="星河读书社", description="虚构社团简介", advisor_contact="teacher@example.com"
    )

    result = club_service.create_registration_application(db, student, body)

    assert result["review_status"] == "DRAFT"
    assert result["applicant_user_id"] == student.user_id
    assert result["applicant_display_name"] == "学生一"
    assert db.commits == 1
    assert len(db.objects(ClubRegistrationApplication)) == 1
    assert event_calls["audits"][0]["action"] == "CLUB_REGISTRATION_CREATE"


def test_review_registration_requires_r03(db, student, event_calls):
    with pytest.raises(AppError) as error:
        club_service.review_registration_application(
            db, student, 11, ReviewRequest(decision="APPROVED", comment="ok")
        )
    assert error.value.code == 40301


def test_review_registration_approves_and_grants_club_scoped_r02(
    db, manager, event_calls, monkeypatch
):
    application = make_registration(status=ReviewStatus.PENDING)
    monkeypatch.setattr(
        club_repository,
        "get_registration_application",
        lambda database, application_id, for_update=False: application,
    )
    monkeypatch.setattr(
        club_repository, "get_club_by_registration_application", lambda database, application_id: None
    )
    monkeypatch.setattr(club_repository, "get_club_by_name", lambda database, name: None)

    result = club_service.review_registration_application(
        db, manager, application.id, ReviewRequest(decision="APPROVED", comment="材料齐全")
    )

    assert application.review_status == ReviewStatus.APPROVED
    assert application.reviewed_by == manager.user_id
    assert result["application"]["review_status"] == "APPROVED"
    assert result["club_authorization"] == {
        "club_id": result["club"]["id"],
        "user_id": application.applicant_user_id,
        "role_code": "R02",
    }
    clubs = db.objects(Club)
    assert len(clubs) == 1
    assert clubs[0].registration_application_id == application.id
    assignments = db.objects(ClubRoleAssignment)
    assert len(assignments) == 1
    assert assignments[0].user_id == application.applicant_user_id
    assert assignments[0].club_id == clubs[0].id
    assert assignments[0].role_code == "R02"
    members = db.objects(ClubMember)
    assert len(members) == 1
    assert members[0].user_id == application.applicant_user_id
    assert event_calls["notifications"][0][0] == "user"
    assert event_calls["notifications"][0][2]["event_type"] == "CLUB_REGISTRATION_APPROVED"


def test_review_registration_rejection_creates_no_club(db, manager, event_calls, monkeypatch):
    application = make_registration(status=ReviewStatus.PENDING)
    monkeypatch.setattr(
        club_repository,
        "get_registration_application",
        lambda database, application_id, for_update=False: application,
    )

    result = club_service.review_registration_application(
        db, manager, application.id, ReviewRequest(decision="REJECTED", comment="材料不完整")
    )

    assert application.review_status == ReviewStatus.REJECTED
    assert application.review_comment == "材料不完整"
    assert db.objects(Club) == []
    assert db.objects(ClubRoleAssignment) == []
    assert result["club"] is None
    assert result["club_authorization"] is None
    assert event_calls["notifications"][0][2]["event_type"] == "CLUB_REGISTRATION_REJECTED"


def test_review_registration_rejection_requires_reason(db, manager, event_calls, monkeypatch):
    application = make_registration(status=ReviewStatus.PENDING)
    monkeypatch.setattr(
        club_repository,
        "get_registration_application",
        lambda database, application_id, for_update=False: application,
    )

    with pytest.raises(AppError) as error:
        club_service.review_registration_application(
            db, manager, application.id, ReviewRequest(decision="REJECTED", comment=None)
        )
    assert error.value.code == 40001
    assert application.review_status == ReviewStatus.PENDING


def test_review_registration_blocks_applicant_as_reviewer(db, manager, event_calls, monkeypatch):
    application = make_registration(status=ReviewStatus.PENDING, applicant_user_id=manager.user_id)
    monkeypatch.setattr(
        club_repository,
        "get_registration_application",
        lambda database, application_id, for_update=False: application,
    )

    with pytest.raises(AppError) as error:
        club_service.review_registration_application(
            db, manager, application.id, ReviewRequest(decision="APPROVED", comment=None)
        )
    assert error.value.code == 40301


def test_update_registration_only_owner_in_editable_status(db, student, event_calls, monkeypatch):
    application = make_registration(status=ReviewStatus.DRAFT)
    monkeypatch.setattr(
        club_repository,
        "get_registration_application",
        lambda database, application_id, for_update=False: application,
    )

    result = club_service.update_registration_application(
        db, student, application.id, ClubRegistrationUpdateRequest(proposed_name="新名字")
    )
    assert result["proposed_name"] == "新名字"

    other = type(student)(
        user_id=2,
        username="leader01",
        display_name="负责人一",
        system_roles={"R01"},
        club_leader_ids={1},
    )
    with pytest.raises(AppError) as error:
        club_service.update_registration_application(
            db, other, application.id, ClubRegistrationUpdateRequest(proposed_name="越权")
        )
    assert error.value.code == 40301

    application.review_status = ReviewStatus.PENDING
    with pytest.raises(AppError) as error:
        club_service.update_registration_application(
            db, student, application.id, ClubRegistrationUpdateRequest(proposed_name="待审核修改")
        )
    assert error.value.code == 40901


def test_submit_and_withdraw_registration_follow_state_machine(
    db, student, event_calls, monkeypatch
):
    application = make_registration(status=ReviewStatus.DRAFT)
    monkeypatch.setattr(
        club_repository,
        "get_registration_application",
        lambda database, application_id, for_update=False: application,
    )

    result = club_service.submit_registration_application(db, student, application.id)
    assert result["review_status"] == "PENDING"
    assert application.submitted_at is not None
    assert event_calls["notifications"][0][0] == "managers"

    with pytest.raises(AppError) as error:
        club_service.submit_registration_application(db, student, application.id)
    assert error.value.code == 40901

    result = club_service.withdraw_registration_application(db, student, application.id)
    assert result["review_status"] == "WITHDRAWN"

    with pytest.raises(AppError) as error:
        club_service.withdraw_registration_application(db, student, application.id)
    assert error.value.code == 40901


def test_update_club_requires_target_club_r02(db, student, leader, event_calls, monkeypatch):
    club = make_club()
    monkeypatch.setattr(
        club_repository,
        "get_club",
        lambda database, club_id, for_update=False: club,
    )
    monkeypatch.setattr(club_repository, "get_club_by_name", lambda database, name: None)

    with pytest.raises(AppError) as error:
        club_service.update_club(db, student, club.id, ClubUpdateRequest(name="新社团名"))
    assert error.value.code == 40302

    result = club_service.update_club(db, leader, club.id, ClubUpdateRequest(name="新社团名"))
    assert result["name"] == "新社团名"
    assert event_calls["audits"][0]["action"] == "CLUB_PROFILE_UPDATE"


def test_list_registration_applications_scopes_r03_and_owner(db, manager, student, monkeypatch):
    captured = {}

    def fake_list(database, **kwargs):
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(club_repository, "list_registration_applications", fake_list)

    club_service.list_registration_applications(db, manager, page=1, page_size=20)
    assert captured["applicant_user_id"] is None

    club_service.list_registration_applications(db, student, page=1, page_size=20)
    assert captured["applicant_user_id"] == student.user_id


def test_m02_route_contract_is_preserved():
    paths = app.openapi()["paths"]
    expected = {
        ("/api/v1/club-registration-applications", "post"),
        ("/api/v1/club-registration-applications", "get"),
        ("/api/v1/club-registration-applications/{application_id}", "patch"),
        ("/api/v1/club-registration-applications/{application_id}/submit", "post"),
        ("/api/v1/club-registration-applications/{application_id}/withdraw", "post"),
        ("/api/v1/club-registration-applications/{application_id}/review", "post"),
        ("/api/v1/clubs", "get"),
        ("/api/v1/clubs/{club_id}", "get"),
        ("/api/v1/clubs/{club_id}", "patch"),
        ("/api/v1/annual-reviews", "post"),
        ("/api/v1/annual-reviews", "get"),
        ("/api/v1/annual-reviews/{application_id}", "patch"),
        ("/api/v1/annual-reviews/{application_id}/submit", "post"),
        ("/api/v1/annual-reviews/{application_id}/withdraw", "post"),
        ("/api/v1/annual-reviews/{application_id}/review", "post"),
        ("/api/v1/membership-applications", "post"),
        ("/api/v1/membership-applications", "get"),
        ("/api/v1/membership-applications/{application_id}/withdraw", "post"),
        ("/api/v1/membership-applications/{application_id}/process", "post"),
        ("/api/v1/clubs/{club_id}/members", "get"),
        ("/api/v1/clubs/{club_id}/members/{member_id}", "patch"),
    }
    for path, method in expected:
        assert path in paths, path
        assert method in paths[path], (path, method)
