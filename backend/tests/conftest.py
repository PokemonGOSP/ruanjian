import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_principal
from app.core.permissions import Principal
from app.db.session import get_db
from app.main import app


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def r01():
    return Principal(
        user_id=1,
        username="student01",
        display_name="学生一",
        system_roles={"R01"},
        club_leader_ids=set(),
    )


@pytest.fixture
def r02():
    return Principal(
        user_id=3,
        username="leader01",
        display_name="社团负责人一",
        system_roles={"R01"},
        club_leader_ids={1, 3},
    )


@pytest.fixture
def r03():
    return Principal(
        user_id=5,
        username="manager01",
        display_name="社团管理人员",
        system_roles={"R01", "R03"},
        club_leader_ids=set(),
    )


@pytest.fixture
def r04():
    return Principal(
        user_id=6,
        username="admin01",
        display_name="系统管理员",
        system_roles={"R01", "R04"},
        club_leader_ids=set(),
    )


@pytest.fixture
def override_auth():
    def _override(principal: Principal) -> None:
        app.dependency_overrides[get_current_principal] = lambda: principal

    return _override


@pytest.fixture
def override_db():
    def _override(db) -> None:
        app.dependency_overrides[get_db] = lambda: db

    return _override
