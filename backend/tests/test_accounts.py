from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_principal
from app.core.permissions import Principal
from app.db.models.domain import AccountStatus, AuditLog, SystemRoleAssignment, User
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


class CreateFakeDb:
    def __init__(self, existing_username: bool = False) -> None:
        self.existing_username = existing_username
        self.added = []
        self.committed = False

    def scalar(self, _):
        return 1 if self.existing_username else None

    def add(self, item):
        self.added.append(item)

    def flush(self):
        user = next(item for item in self.added if isinstance(item, User))
        user.id = 9

    def commit(self):
        self.committed = True


class UpdateFakeDb:
    def __init__(self, account: User | None) -> None:
        self.account = account
        self.added = []
        self.committed = False
        self.scalars_call_count = 0

    def get(self, _, account_id: int):
        return self.account if self.account is not None and self.account.id == account_id else None

    def scalars(self, _):
        self.scalars_call_count += 1
        if self.scalars_call_count == 1:
            return SimpleNamespace(all=lambda: ["R01"])
        return SimpleNamespace(all=lambda: [])

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed = True


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


def fake_db():
    yield FakeDb()


def create_fake_db(existing_username: bool = False):
    instance = CreateFakeDb(existing_username=existing_username)

    def dependency():
        yield instance

    return dependency, instance


def update_fake_db(account: User | None):
    instance = UpdateFakeDb(account)

    def dependency():
        yield instance

    return dependency, instance


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


def test_r04_can_create_local_account_with_r01_and_audit_record():
    dependency, fake_db_instance = create_fake_db()
    app.dependency_overrides[get_db] = dependency
    app.dependency_overrides[get_current_principal] = principal_with("R04")
    client = TestClient(app)

    response = client.post(
        "/api/v1/accounts",
        json={"username": "newstudent", "display_name": "新同学", "password": "NewStudent123!"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["system_roles"] == ["R01"]
    assert fake_db_instance.committed is True
    assert any(isinstance(item, User) and item.password_hash != "NewStudent123!" for item in fake_db_instance.added)
    assert any(
        isinstance(item, SystemRoleAssignment) and item.role_code == "R01" and item.user_id == 9
        for item in fake_db_instance.added
    )
    assert any(
        isinstance(item, AuditLog) and item.action == "ACCOUNT_CREATED" and "NewStudent123!" not in item.detail_json
        for item in fake_db_instance.added
    )


def test_create_account_rejects_duplicate_username():
    dependency, _ = create_fake_db(existing_username=True)
    app.dependency_overrides[get_db] = dependency
    app.dependency_overrides[get_current_principal] = principal_with("R04")
    client = TestClient(app)

    response = client.post(
        "/api/v1/accounts",
        json={"username": "student01", "display_name": "重复账号", "password": "NewStudent123!"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == 40902


def test_r04_can_disable_account_and_get_audited_result():
    account = User(
        id=2,
        username="student02",
        password_hash="must-not-be-returned",
        display_name="学生二",
        status=AccountStatus.NORMAL,
    )
    dependency, fake_db_instance = update_fake_db(account)
    app.dependency_overrides[get_db] = dependency
    app.dependency_overrides[get_current_principal] = principal_with("R04")
    client = TestClient(app)

    response = client.patch("/api/v1/accounts/2", json={"status": "DISABLED"})

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "DISABLED"
    assert fake_db_instance.committed is True
    assert any(isinstance(item, AuditLog) and item.action == "ACCOUNT_UPDATED" for item in fake_db_instance.added)


def test_update_account_returns_404_for_missing_account():
    dependency, _ = update_fake_db(None)
    app.dependency_overrides[get_db] = dependency
    app.dependency_overrides[get_current_principal] = principal_with("R04")
    client = TestClient(app)

    response = client.patch("/api/v1/accounts/999", json={"status": "DISABLED"})

    assert response.status_code == 404
    assert response.json()["code"] == 40401


def test_update_account_rejects_no_effect_change():
    account = User(
        id=2,
        username="student02",
        password_hash="must-not-be-returned",
        display_name="学生二",
        status=AccountStatus.NORMAL,
    )
    dependency, _ = update_fake_db(account)
    app.dependency_overrides[get_db] = dependency
    app.dependency_overrides[get_current_principal] = principal_with("R04")
    client = TestClient(app)

    response = client.patch("/api/v1/accounts/2", json={"status": "NORMAL"})

    assert response.status_code == 409
    assert response.json()["code"] == 40901
