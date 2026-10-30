import pytest

from app.core.exceptions import AppError
from app.db.models.domain import ReadStatus
from app.schemas.notification import ManagementNotificationRequest
from app.services import notification_service
from app.services.notification_service import notify_many, validate_management_request


class RecordingDb:
    def __init__(self):
        self.rows = []

    def add(self, row):
        self.rows.append(row)

    def add_all(self, rows):
        self.rows.extend(rows)


class FakeScalars:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class FakeListDb:
    def scalar(self, _stmt):
        return 0

    def scalars(self, _stmt):
        return FakeScalars([])


class FakeNotification:
    id = 1
    recipient_user_id = 2
    read_status = ReadStatus.UNREAD
    title = "通知"
    content = "内容"
    event_type = "TEST"
    related_type = None
    related_id = None
    created_at = None
    read_at = None


class FakeGetDb:
    def get(self, _model, _key):
        return FakeNotification()


class FakeWriteDb:
    def __init__(self):
        self.rows = []
        self.committed = False

    def add(self, row):
        self.rows.append(row)

    def add_all(self, rows):
        self.rows.extend(rows)

    def commit(self):
        self.committed = True


def test_validate_management_request_rejects_mixed_targets():
    body = ManagementNotificationRequest(
        title="测试",
        content="内容",
        target_type="USERS",
        user_ids=[1],
        club_ids=[2],
    )
    with pytest.raises(AppError) as exc:
        validate_management_request(body)
    assert exc.value.code == 40002


def test_validate_management_request_requires_targets():
    body = ManagementNotificationRequest(title="测试", content="内容", target_type="ROLES")
    with pytest.raises(AppError) as exc:
        validate_management_request(body)
    assert exc.value.code == 40002


def test_notify_many_deduplicates_and_sorts_recipients():
    db = RecordingDb()
    rows = notify_many(db, [3, 1, 3, 2], title="标题", content="内容", event_type="ACTIVITY_CANCELLED")
    assert [row.recipient_user_id for row in rows] == [1, 2, 3]
    assert all(row.read_status == ReadStatus.UNREAD for row in rows)


def test_management_notification_requires_r03(client, override_auth, override_db, r01):
    override_auth(r01)
    override_db(None)
    response = client.post(
        "/api/v1/notifications/management",
        json={"title": "标题", "content": "内容", "target_type": "USERS", "user_ids": [1]},
    )
    assert response.status_code == 403
    assert response.json()["code"] == 40301


def test_management_notification_publishes_for_r03(client, monkeypatch, override_auth, override_db, r03):
    db = FakeWriteDb()
    override_auth(r03)
    override_db(db)
    monkeypatch.setattr(notification_service, "publish_management_notice", lambda _db, _body: 2)
    response = client.post(
        "/api/v1/notifications/management",
        json={"title": "标题", "content": "内容", "target_type": "ROLES", "role_codes": ["R02"]},
    )
    assert response.status_code == 200
    assert response.json()["data"] == {"created_count": 2, "recipient_count": 2, "target_type": "ROLES"}
    assert db.committed is True


def test_mark_read_rejects_other_recipient(client, override_auth, override_db, r01):
    override_auth(r01)
    override_db(FakeGetDb())
    response = client.post("/api/v1/notifications/1/read")
    assert response.status_code == 403
    assert response.json()["code"] == 40301


def test_list_notifications_is_scoped_to_current_user(client, override_auth, override_db, r01):
    override_auth(r01)
    override_db(FakeListDb())
    response = client.get("/api/v1/notifications")
    assert response.status_code == 200
    assert response.json()["data"]["total"] == 0
    assert response.json()["data"]["items"] == []


# ---------------------------------------------------------------- Service 层
class SequencedScalarsDb:
    def __init__(self, results):
        self.results = list(results)
        self.rows = []

    def scalars(self, _stmt):
        return FakeScalars(self.results.pop(0))

    def add_all(self, rows):
        self.rows.extend(rows)

    def add(self, row):
        self.rows.append(row)


def test_notify_creates_unread_notification():
    db = RecordingDb()
    row = notification_service.notify(
        db,
        recipient_user_id=2,
        title="标题",
        content="内容",
        event_type="TEST",
        related_type="ACTIVITY",
        related_id=9,
    )
    assert row.recipient_user_id == 2
    assert row.read_status == ReadStatus.UNREAD
    assert row.related_type == "ACTIVITY"
    assert row.related_id == 9


def test_notification_service_deduplicates_and_truncates_title():
    db = FakeWriteDb()
    service = notification_service.NotificationService(db)
    count = service.notify_users(
        [3, 1, 3],
        title="长" * 250,
        content="内容",
        event_type="ACTIVITY_CANCELLED",
        related_id=7,
    )
    assert count == 2
    assert [row.recipient_user_id for row in db.rows] == [1, 3]
    assert all(len(row.title) == 200 for row in db.rows)
    assert all(row.related_type == "ACTIVITY" for row in db.rows)


def test_validate_roles_rejects_mixed_users():
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="ROLES", role_codes=["R02"], user_ids=[1]
    )
    with pytest.raises(AppError) as exc:
        validate_management_request(body)
    assert exc.value.code == 40002


def test_validate_clubs_rejects_mixed_roles():
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="CLUBS", club_ids=[1], role_codes=["R02"]
    )
    with pytest.raises(AppError) as exc:
        validate_management_request(body)
    assert exc.value.code == 40002


def test_resolve_users_deduplicates_and_checks_existence():
    db = SequencedScalarsDb([[1, 2]])
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="USERS", user_ids=[2, 1, 2]
    )
    assert notification_service.resolve_management_recipients(db, body) == [1, 2]


def test_resolve_users_rejects_missing_user():
    db = SequencedScalarsDb([[1]])
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="USERS", user_ids=[1, 2]
    )
    with pytest.raises(AppError) as exc:
        notification_service.resolve_management_recipients(db, body)
    assert exc.value.code == 40002


def test_resolve_roles_unions_system_and_club_roles():
    db = SequencedScalarsDb([[5], [3, 5]])
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="ROLES", role_codes=["R03", "R02"]
    )
    assert notification_service.resolve_management_recipients(db, body) == [3, 5]


def test_resolve_roles_rejects_empty_audience():
    db = SequencedScalarsDb([[], []])
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="ROLES", role_codes=["R04", "R02"]
    )
    with pytest.raises(AppError) as exc:
        notification_service.resolve_management_recipients(db, body)
    assert exc.value.code == 40002


def test_resolve_clubs_unions_members_and_leaders():
    db = SequencedScalarsDb([[1], [1, 2], [2, 3]])
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="CLUBS", club_ids=[1]
    )
    assert notification_service.resolve_management_recipients(db, body) == [1, 2, 3]


def test_resolve_clubs_rejects_missing_club():
    db = SequencedScalarsDb([[]])
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="CLUBS", club_ids=[9]
    )
    with pytest.raises(AppError) as exc:
        notification_service.resolve_management_recipients(db, body)
    assert exc.value.code == 40002


def test_resolve_clubs_rejects_empty_audience():
    db = SequencedScalarsDb([[1], [], []])
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="CLUBS", club_ids=[1]
    )
    with pytest.raises(AppError) as exc:
        notification_service.resolve_management_recipients(db, body)
    assert exc.value.code == 40002


def test_publish_management_notice_writes_rows():
    db = SequencedScalarsDb([[1, 2]])
    body = ManagementNotificationRequest(
        title="测试", content="内容", target_type="USERS", user_ids=[1, 2]
    )
    assert notification_service.publish_management_notice(db, body) == 2
    assert len(db.rows) == 2
    assert all(row.event_type == "MANAGEMENT_NOTICE" for row in db.rows)
    assert all(row.related_type == "MANAGEMENT_NOTICE" for row in db.rows)
