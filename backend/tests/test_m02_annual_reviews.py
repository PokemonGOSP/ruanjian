import pytest

from app.core.exceptions import AppError
from app.db.models.domain import AnnualReviewApplication, Club, ReviewStatus
from app.repositories import club_repository
from app.schemas.business import ReviewRequest
from app.schemas.club import AnnualReviewCreateRequest, AnnualReviewUpdateRequest
from app.services import club_service
from tests.helpers import make_annual_review, make_club


def test_create_annual_review_requires_target_club_r02(db, student, event_calls, monkeypatch):
    club = make_club()
    monkeypatch.setattr(club_repository, "get_club", lambda database, club_id, for_update=False: club)

    with pytest.raises(AppError) as error:
        club_service.create_annual_review(
            db, student, AnnualReviewCreateRequest(club_id=club.id, review_year=2026, materials="材料")
        )
    assert error.value.code == 40302
    assert db.objects(AnnualReviewApplication) == []


def test_create_annual_review_rejects_duplicate_year(db, leader, event_calls, monkeypatch):
    club = make_club()
    monkeypatch.setattr(club_repository, "get_club", lambda database, club_id, for_update=False: club)
    monkeypatch.setattr(
        club_repository,
        "get_annual_review_by_club_year",
        lambda database, club_id, review_year: make_annual_review(),
    )

    with pytest.raises(AppError) as error:
        club_service.create_annual_review(
            db, leader, AnnualReviewCreateRequest(club_id=club.id, review_year=2026, materials="材料")
        )
    assert error.value.code == 40902


def test_create_annual_review_starts_as_draft(db, leader, event_calls, monkeypatch):
    club = make_club()
    monkeypatch.setattr(club_repository, "get_club", lambda database, club_id, for_update=False: club)
    monkeypatch.setattr(
        club_repository, "get_annual_review_by_club_year", lambda database, club_id, review_year: None
    )

    result = club_service.create_annual_review(
        db, leader, AnnualReviewCreateRequest(club_id=club.id, review_year=2026, materials="材料")
    )
    assert result["review_status"] == "DRAFT"
    assert result["club_name"] == club.name
    assert db.commits == 1


def test_submit_and_withdraw_annual_review(db, leader, event_calls, monkeypatch):
    application = make_annual_review(status=ReviewStatus.DRAFT)
    monkeypatch.setattr(
        club_repository,
        "get_annual_review",
        lambda database, application_id, for_update=False: application,
    )
    monkeypatch.setattr(
        club_repository, "get_club", lambda database, club_id, for_update=False: make_club()
    )

    result = club_service.submit_annual_review(db, leader, application.id)
    assert result["review_status"] == "PENDING"
    assert application.submitted_at is not None
    assert event_calls["notifications"][0][0] == "managers"

    result = club_service.withdraw_annual_review(db, leader, application.id)
    assert result["review_status"] == "WITHDRAWN"

    with pytest.raises(AppError) as error:
        club_service.withdraw_annual_review(db, leader, application.id)
    assert error.value.code == 40901


def test_update_annual_review_only_in_editable_status(db, leader, event_calls, monkeypatch):
    application = make_annual_review(status=ReviewStatus.DRAFT)
    monkeypatch.setattr(
        club_repository,
        "get_annual_review",
        lambda database, application_id, for_update=False: application,
    )
    monkeypatch.setattr(
        club_repository, "get_annual_review_by_club_year", lambda database, club_id, review_year: None
    )
    monkeypatch.setattr(
        club_repository, "get_club", lambda database, club_id, for_update=False: make_club()
    )

    result = club_service.update_annual_review(
        db, leader, application.id, AnnualReviewUpdateRequest(materials="新材料")
    )
    assert result["materials"] == "新材料"

    application.review_status = ReviewStatus.PENDING
    with pytest.raises(AppError) as error:
        club_service.update_annual_review(
            db, leader, application.id, AnnualReviewUpdateRequest(materials="待审核修改")
        )
    assert error.value.code == 40901


def test_review_annual_review_saves_result_without_freezing_club(
    db, manager, event_calls, monkeypatch
):
    application = make_annual_review(status=ReviewStatus.PENDING, submitted_by=2)
    club = make_club()
    monkeypatch.setattr(
        club_repository,
        "get_annual_review",
        lambda database, application_id, for_update=False: application,
    )
    monkeypatch.setattr(club_repository, "get_club", lambda database, club_id, for_update=False: club)

    result = club_service.review_annual_review(
        db, manager, application.id, ReviewRequest(decision="REJECTED", comment="材料不完整")
    )

    assert result["review_status"] == "REJECTED"
    assert application.review_comment == "材料不完整"
    assert application.reviewed_by == manager.user_id
    assert db.objects(Club) == []
    assert event_calls["notifications"][0][0] == "user"
    assert event_calls["notifications"][0][2]["event_type"] == "ANNUAL_REVIEW_REJECTED"


def test_review_annual_review_rejection_requires_comment(db, manager, event_calls, monkeypatch):
    application = make_annual_review(status=ReviewStatus.PENDING, submitted_by=2)
    monkeypatch.setattr(
        club_repository,
        "get_annual_review",
        lambda database, application_id, for_update=False: application,
    )

    with pytest.raises(AppError) as error:
        club_service.review_annual_review(
            db, manager, application.id, ReviewRequest(decision="REJECTED", comment=None)
        )
    assert error.value.code == 40001
    assert application.review_status == ReviewStatus.PENDING


def test_review_annual_review_blocks_same_person(db, manager, event_calls, monkeypatch):
    application = make_annual_review(status=ReviewStatus.PENDING, submitted_by=manager.user_id)
    monkeypatch.setattr(
        club_repository,
        "get_annual_review",
        lambda database, application_id, for_update=False: application,
    )

    with pytest.raises(AppError) as error:
        club_service.review_annual_review(
            db, manager, application.id, ReviewRequest(decision="APPROVED", comment=None)
        )
    assert error.value.code == 40301


def test_list_annual_reviews_scope(db, student, leader, manager, monkeypatch):
    captured = {}

    def fake_list(database, **kwargs):
        captured.update(kwargs)
        return [], 0

    monkeypatch.setattr(club_repository, "list_annual_reviews", fake_list)

    with pytest.raises(AppError) as error:
        club_service.list_annual_reviews(db, student, page=1, page_size=20)
    assert error.value.code == 40301

    club_service.list_annual_reviews(db, leader, page=1, page_size=20)
    assert captured["club_ids"] == [1]

    club_service.list_annual_reviews(db, manager, page=1, page_size=20)
    assert captured["club_ids"] is None
