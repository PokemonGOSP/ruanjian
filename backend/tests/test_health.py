from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.db.session import get_db
from app.main import app


class FakeDb:
    def execute(self, _):
        return SimpleNamespace(all=lambda: [(1,)])


def fake_db():
    yield FakeDb()


app.dependency_overrides[get_db] = fake_db
client = TestClient(app)


def test_health_reports_service_and_database_up():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"] == {"service": "up", "database": "up"}
