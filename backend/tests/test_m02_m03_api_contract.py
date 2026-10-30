from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_principal
from app.core.permissions import Principal
from app.db.session import get_db
from app.main import app
from app.services import club_service, member_service


@pytest.fixture
def client():
    principal = Principal(
        user_id=1,
        username="student01",
        display_name="学生一",
        system_roles={"R01"},
        club_leader_ids={1},
    )
    previous_db = app.dependency_overrides.get(get_db)
    previous_principal = app.dependency_overrides.get(get_current_principal)
    app.dependency_overrides[get_db] = lambda: object()
    app.dependency_overrides[get_current_principal] = lambda: principal
    try:
        yield TestClient(app)
    finally:
        if previous_db is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_db
        if previous_principal is None:
            app.dependency_overrides.pop(get_current_principal, None)
        else:
            app.dependency_overrides[get_current_principal] = previous_principal


def _registration_data():
    return {
        "id": 11,
        "applicant_user_id": 1,
        "applicant_display_name": "学生一",
        "proposed_name": "星河读书社",
        "description": "虚构社团简介",
        "advisor_contact": None,
        "review_status": "DRAFT",
        "review_comment": None,
        "reviewed_by": None,
        "submitted_at": None,
        "reviewed_at": None,
        "created_at": datetime(2026, 1, 1, 9, 0, 0),
    }


def test_create_registration_route_serializes_domain_response(client, monkeypatch):
    monkeypatch.setattr(
        club_service,
        "create_registration_application",
        lambda db, principal, body: _registration_data(),
    )

    response = client.post(
        "/api/v1/club-registration-applications",
        json={
            "proposed_name": "星河读书社",
            "description": "虚构社团简介",
            "advisor_contact": None,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == 0
    assert payload["data"]["review_status"] == "DRAFT"
    assert payload["data"]["proposed_name"] == "星河读书社"


def test_club_list_route_returns_page_data(client, monkeypatch):
    monkeypatch.setattr(
        club_service,
        "list_clubs",
        lambda db, page, page_size: {
            "items": [
                {
                    "id": 1,
                    "registration_application_id": 11,
                    "name": "星河读书社",
                    "description": "虚构社团",
                    "advisor_contact": None,
                    "created_at": datetime(2026, 1, 1, 9, 0, 0),
                    "updated_at": datetime(2026, 1, 1, 9, 0, 0),
                }
            ],
            "page": page,
            "page_size": page_size,
            "total": 1,
        },
    )

    response = client.get("/api/v1/clubs?page=1&page_size=20")

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["items"][0]["name"] == "星河读书社"


def test_membership_process_route_serializes_member(client, monkeypatch):
    monkeypatch.setattr(
        member_service,
        "process_membership_application",
        lambda db, principal, application_id, body: {
            "application": {
                "id": 41,
                "club_id": 1,
                "club_name": "星河读书社",
                "applicant_user_id": 1,
                "applicant_display_name": "学生一",
                "application_type": "JOIN",
                "reason": "想加入",
                "status": "APPROVED",
                "processed_by": 2,
                "processed_by_display_name": "负责人一",
                "process_comment": "欢迎",
                "created_at": datetime(2026, 1, 1, 9, 0, 0),
                "processed_at": datetime(2026, 1, 2, 9, 0, 0),
            },
            "member": {
                "id": 31,
                "club_id": 1,
                "user_id": 1,
                "username": "student01",
                "display_name": "学生一",
                "position_name": None,
                "status": "ACTIVE",
                "joined_at": datetime(2026, 1, 2, 9, 0, 0),
                "exited_at": None,
            },
        },
    )

    response = client.post(
        "/api/v1/membership-applications/41/process",
        json={"decision": "APPROVED", "comment": "欢迎"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["application"]["status"] == "APPROVED"
    assert response.json()["data"]["member"]["status"] == "ACTIVE"


def test_annual_review_route_serializes_domain_response(client, monkeypatch):
    monkeypatch.setattr(
        club_service,
        "create_annual_review",
        lambda db, principal, body: {
            "id": 21,
            "club_id": 1,
            "club_name": "星河读书社",
            "review_year": 2099,
            "submitted_by": 1,
            "submitter_display_name": "学生一",
            "materials": "虚构年审材料",
            "review_status": "DRAFT",
            "review_comment": None,
            "reviewed_by": None,
            "submitted_at": None,
            "reviewed_at": None,
            "created_at": datetime(2026, 1, 1, 9, 0, 0),
        },
    )

    response = client.post(
        "/api/v1/annual-reviews",
        json={"club_id": 1, "review_year": 2099, "materials": "虚构年审材料"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["review_status"] == "DRAFT"
    assert response.json()["data"]["club_name"] == "星河读书社"


def test_page_size_validation_uses_contract_error_code(client):
    response = client.get("/api/v1/clubs?page=1&page_size=101")
    assert response.status_code == 422
    assert response.json()["code"] == 40001
