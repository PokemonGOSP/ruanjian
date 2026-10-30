import pytest

from app.core.exceptions import AppError
from app.db.models.domain import ReviewStatus
from app.repositories import club_repository, member_repository
from app.services import club_member_statistics
from tests.helpers import make_club


def test_statistics_requires_r02_or_r03(db, student, monkeypatch):
    with pytest.raises(AppError) as error:
        club_member_statistics.club_member_statistics(db, student)
    assert error.value.code == 40301


def test_statistics_r02_cannot_query_other_club(db, leader, monkeypatch):
    with pytest.raises(AppError) as error:
        club_member_statistics.club_member_statistics(db, leader, club_id=2)
    assert error.value.code == 40302


def test_statistics_r02_scopes_to_own_clubs(db, leader, monkeypatch):
    clubs = [make_club(club_id=1, name="星河读书社")]
    monkeypatch.setattr(club_repository, "all_clubs", lambda database, club_ids=None: clubs)
    monkeypatch.setattr(
        member_repository,
        "member_counts_by_club",
        lambda database, club_ids=None: {1: {"ACTIVE": 3, "EXITED": 1}},
    )
    monkeypatch.setattr(
        member_repository, "pending_application_counts_by_club", lambda database, club_ids=None: {1: 2}
    )
    monkeypatch.setattr(
        club_repository,
        "annual_review_status_by_year",
        lambda database, club_ids, review_year: {1: ReviewStatus.APPROVED},
    )
    monkeypatch.setattr(
        member_repository, "distinct_active_member_count", lambda database, club_ids=None: 3
    )

    result = club_member_statistics.club_member_statistics(db, leader, review_year=2026)

    assert result["scope"] == "OWN_CLUBS"
    assert result["total_clubs"] == 1
    assert result["total_active_members"] == 3
    assert result["total_active_memberships"] == 3
    assert result["total_memberships"] == 4
    assert result["total_pending_membership_applications"] == 2
    assert result["items"][0]["annual_review_status"] == "APPROVED"


def test_statistics_r03_sees_all_clubs(db, manager, monkeypatch):
    clubs = [make_club(club_id=1, name="星河读书社"), make_club(club_id=2, name="像素创意社")]
    monkeypatch.setattr(club_repository, "all_clubs", lambda database, club_ids=None: clubs)
    monkeypatch.setattr(
        member_repository,
        "member_counts_by_club",
        lambda database, club_ids=None: {
            1: {"ACTIVE": 3, "EXITED": 1},
            2: {"ACTIVE": 2, "EXITED": 0},
        },
    )
    monkeypatch.setattr(
        member_repository,
        "pending_application_counts_by_club",
        lambda database, club_ids=None: {1: 1},
    )
    monkeypatch.setattr(
        club_repository,
        "annual_review_status_by_year",
        lambda database, club_ids, review_year: {2: ReviewStatus.PENDING},
    )
    monkeypatch.setattr(
        member_repository, "distinct_active_member_count", lambda database, club_ids=None: 5
    )

    result = club_member_statistics.club_member_statistics(db, manager, review_year=2026)

    assert result["scope"] == "ALL"
    assert result["total_clubs"] == 2
    assert result["total_active_members"] == 5
    assert result["total_active_memberships"] == 5
    assert result["total_memberships"] == 6
    assert result["total_pending_membership_applications"] == 1
    assert [item["club_id"] for item in result["items"]] == [1, 2]
    assert result["items"][0]["annual_review_status"] is None
    assert result["items"][1]["annual_review_status"] == "PENDING"
