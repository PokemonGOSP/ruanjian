from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_principal
from app.core.permissions import Principal
from app.db.models.domain import AccountStatus, User
from app.db.session import get_db
from app.main import app


class FakeDb:
    def __init__(self) -> None:
        self.execute_call_count = 0
        self.users = [
            User(
                id=1,
                username="student01",
                password_hash="must-not-be-returned",
                display_name="学生一",
                status=AccountStatus.NORMAL,
            ),
            User(
                id=6,
                username="admin01",
                password_hash="must-not-be-returned",
                display_name="系统管理员",
                status=AccountStatus.NORMAL,
            ),
        ]

    def scalar(self, _):
        return len(self.users)

    def scalars(self, _):
        return SimpleNamespace(all=lambda: self.users)

    def execute(self, _):
        self.execute_call_count += 1
        if self.execute_call_count == 1:
            return SimpleNamespace(all=lambda: [(1, "R01"), (6, "R01"), (6, "R04")])
        return SimpleNamespace(all=lambda: [(6, 101)])


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def fake_db():
    yield FakeDb()


def principal_with(*roles: str):
    def dependency():
        return Principal(
            user_id=6,
            username="admin01",
            display_name="系统管理员",
            system_roles=set(roles),
            club_leader_ids=set(),
        )

    return dependency


def test_r04_can_list_accounts_without_credential_material():
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_principal] = principal_with("R04")
    client = TestClient(app)

    response = client.get("/api/v1/accounts?page=1&page_size=20")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 2
    assert body["data"]["items"][1]["system_roles"] == ["R01", "R04"]
    assert "password_hash" not in body["data"]["items"][0]


def test_non_r04_cannot_list_accounts():
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_principal] = principal_with("R03")
    client = TestClient(app)

    response = client.get("/api/v1/accounts")

    assert response.status_code == 403
    assert response.json()["code"] == 40301


def test_account_list_rejects_invalid_page_size():
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_principal] = principal_with("R04")
    client = TestClient(app)

    response = client.get("/api/v1/accounts?page_size=101")

    assert response.status_code == 422
    assert response.json()["code"] == 40001
