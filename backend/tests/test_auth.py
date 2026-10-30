from types import SimpleNamespace

import jwt
from fastapi.testclient import TestClient

from app.api.deps import get_current_principal
from app.api.v1 import auth as auth_routes
from app.core.config import get_settings
from app.core.permissions import Principal
from app.core.security import hash_password
from app.db.models.domain import AccountStatus
from app.db.session import get_db
from app.main import app
from app.services import auth_service


class FakeDb:
    def execute(self, _):
        return SimpleNamespace(all=lambda: [])


def fake_db():
    yield FakeDb()


def fake_principal():
    return Principal(
        user_id=1,
        username="student01",
        display_name="学生一",
        system_roles={"R01"},
        club_leader_ids=set(),
    )


app.dependency_overrides[get_db] = fake_db
client = TestClient(app)


def test_login_returns_valid_jwt(monkeypatch):
    monkeypatch.setattr(
        auth_routes,
        "authenticate_user",
        lambda db, username, password: SimpleNamespace(id=1, username=username),
    )
    response = client.post("/api/v1/auth/login", json={"username": "student01", "password": "Student123!"})
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]
    payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
    assert payload["sub"] == "1"


def test_me_returns_roles_and_club_authorizations():
    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_principal] = fake_principal
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer test"})
    assert response.status_code == 200
    assert response.json()["data"]["username"] == "student01"
    assert response.json()["data"]["system_roles"] == ["R01"]
    app.dependency_overrides.pop(get_current_principal, None)


class ScalarDb:
    def __init__(self, user):
        self.user = user

    def scalar(self, _stmt):
        return self.user


def make_login_user(status=AccountStatus.NORMAL):
    return SimpleNamespace(status=status, password_hash=hash_password("Secret123!"))


def test_authenticate_user_rejects_missing_account():
    assert auth_service.authenticate_user(ScalarDb(None), "nobody", "Secret123!") is None


def test_authenticate_user_rejects_disabled_account():
    user = make_login_user(AccountStatus.DISABLED)
    assert auth_service.authenticate_user(ScalarDb(user), "student01", "Secret123!") is None


def test_authenticate_user_rejects_wrong_password():
    user = make_login_user()
    assert auth_service.authenticate_user(ScalarDb(user), "student01", "wrong-password") is None


def test_authenticate_user_returns_matching_user():
    user = make_login_user()
    assert auth_service.authenticate_user(ScalarDb(user), "student01", "Secret123!") is user
