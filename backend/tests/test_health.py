from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


class FakeDb:
    def execute(self, _):
        return SimpleNamespace(all=lambda: [(1,)])


def fake_db():
    yield FakeDb()


@pytest.fixture
def health_client():
    app.dependency_overrides[get_db] = fake_db
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)


def test_health_reports_service_and_database_up(health_client):
    response = health_client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"] == {"service": "up", "database": "up"}
