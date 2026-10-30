"""M04 活动管理测试。

测试使用内存 Repository/Notifier 替身，不依赖 MySQL，也不把工程配置改成 SQLite。
覆盖 FR-11～FR-16 的正常流程、状态机、资源归属、容量/期限、通知和分页校验。
"""

from datetime import datetime, timedelta
from itertools import count

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_principal
from app.api.v1.activities import get_activity_service
from app.core.permissions import Principal
from app.db.models.domain import (
    Activity,
    ActivityExecutionStatus,
    ActivityRegistration,
    RegistrationStatus,
    ReviewStatus,
    User,
)
from app.main import app
from app.repositories.activity_repository import RegistrationRow
from app.services.activity_service import ActivityService


class FakeRepo:
    def __init__(self, *, role_users=None, users=None):
        self.activities: dict[int, Activity] = {}
        self.registrations: dict[tuple[int, int], ActivityRegistration] = {}
        self.users: dict[int, User] = users or {}
        self.role_users = role_users or {}
        self.commits = 0
        self._activity_ids = count(1)
        self._registration_ids = count(1)

    def add(self, entity):
        if isinstance(entity, Activity):
            if entity.id is None:
                entity.id = next(self._activity_ids)
            self.activities[entity.id] = entity
        elif isinstance(entity, ActivityRegistration):
            if entity.id is None:
                entity.id = next(self._registration_ids)
            self.registrations[(entity.activity_id, entity.user_id)] = entity
        else:  # pragma: no cover - 防御未来误用
            raise TypeError(f"unsupported entity: {type(entity)!r}")

    def commit(self):
        self.commits += 1

    def refresh(self, entity):
        return None

    def get(self, activity_id, *, for_update=False):
        return self.activities.get(activity_id)

    def list_visible(self, *, is_manager, leader_club_ids, page, page_size):
        club_ids = set(leader_club_ids)
        items = [
            activity
            for activity in self.activities.values()
            if is_manager
            or activity.club_id in club_ids
            or (
                activity.review_status == ReviewStatus.APPROVED
                and activity.execution_status != ActivityExecutionStatus.UNPUBLISHED
            )
        ]
        items.sort(key=lambda item: (item.created_at or datetime.min, item.id), reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def get_registration(self, activity_id, user_id):
        return self.registrations.get((activity_id, user_id))

    def count_registered(self, activity_id):
        return sum(
            1
            for (item_activity_id, _), registration in self.registrations.items()
            if item_activity_id == activity_id
            and registration.status == RegistrationStatus.REGISTERED
        )

    def registration_counts(self, activity_ids):
        return {activity_id: self.count_registered(activity_id) for activity_id in activity_ids}

    def registrations_for_user(self, user_id, activity_ids):
        result = {}
        for activity_id in activity_ids:
            registration = self.registrations.get((activity_id, user_id))
            if registration is not None:
                result[activity_id] = registration.status.value
        return result

    def list_registrations(self, activity_id, *, page, page_size):
        rows = [
            registration
            for (item_activity_id, _), registration in self.registrations.items()
            if item_activity_id == activity_id
        ]
        rows.sort(key=lambda item: (item.registered_at or datetime.min, item.id), reverse=True)
        total = len(rows)
        start = (page - 1) * page_size
        selected = rows[start : start + page_size]
        result = []
        for registration in selected:
            user = self.users.get(registration.user_id)
            result.append(
                RegistrationRow(
                    registration,
                    user.username if user else None,
                    user.display_name if user else None,
                )
            )
        return result, total

    def registered_user_ids(self, activity_id):
        return [
            registration.user_id
            for (item_activity_id, _), registration in self.registrations.items()
            if item_activity_id == activity_id
            and registration.status == RegistrationStatus.REGISTERED
        ]

    def active_user_ids_with_system_role(self, role_code):
        return list(self.role_users.get(role_code, []))


class FakeNotifier:
    def __init__(self):
        self.calls = []

    def notify_users(self, user_ids, *, title, content, event_type, related_id=None):
        recipients = sorted(set(user_ids))
        self.calls.append(
            {
                "user_ids": recipients,
                "title": title,
                "content": content,
                "event_type": event_type,
                "related_id": related_id,
            }
        )
        return len(recipients)

    def events(self, event_type):
        return [call for call in self.calls if call["event_type"] == event_type]


class Clock:
    def __init__(self, value):
        self.value = value

    def now(self):
        return self.value

    def advance(self, **kwargs):
        self.value += timedelta(**kwargs)


class Env:
    def __init__(self):
        self.clock = Clock(datetime(2026, 10, 1, 9, 0))
        self.users = {
            1: User(id=1, username="student01", display_name="学生一", password_hash="x"),
            2: User(id=2, username="leader01", display_name="负责人一", password_hash="x"),
            3: User(id=3, username="leader02", display_name="负责人二", password_hash="x"),
            4: User(id=4, username="manager01", display_name="管理员", password_hash="x"),
            5: User(id=5, username="admin01", display_name="系统管理员", password_hash="x"),
            6: User(id=6, username="student02", display_name="学生二", password_hash="x"),
        }
        self.repo = FakeRepo(role_users={"R03": [4]}, users=self.users)
        self.notifier = FakeNotifier()
        self.service = ActivityService(
            db=None, repo=self.repo, notifier=self.notifier, now=self.clock.now
        )
        self.student = Principal(1, "student01", "学生一", {"R01"}, set())
        self.student2 = Principal(6, "student02", "学生二", {"R01"}, set())
        self.leader1 = Principal(2, "leader01", "负责人一", {"R01"}, {1})
        self.leader2 = Principal(3, "leader02", "负责人二", {"R01"}, {2})
        self.manager = Principal(4, "manager01", "管理员", {"R01", "R03"}, set())
        self.admin = Principal(5, "admin01", "系统管理员", {"R01", "R04"}, set())
        self.current = self.student
        self.client = TestClient(app)
        app.dependency_overrides[get_activity_service] = lambda: self.service
        app.dependency_overrides[get_current_principal] = lambda: self.current

    def act_as(self, principal):
        self.current = principal

    def close(self):
        app.dependency_overrides.pop(get_activity_service, None)
        app.dependency_overrides.pop(get_current_principal, None)

    def post(self, url, **kwargs):
        return self.client.post(url, headers={"Authorization": "Bearer test"}, **kwargs)

    def get(self, url, **kwargs):
        return self.client.get(url, headers={"Authorization": "Bearer test"}, **kwargs)

    def patch(self, url, **kwargs):
        return self.client.patch(url, headers={"Authorization": "Bearer test"}, **kwargs)

    def delete(self, url, **kwargs):
        return self.client.delete(url, headers={"Authorization": "Bearer test"}, **kwargs)

    def create_activity(self, *, principal=None, **overrides):
        payload = {
            "club_id": 1,
            "title": "迎新晚会",
            "description": "迎新活动方案",
            "location": "大学生活动中心",
            "starts_at": "2026-11-01T19:00:00",
            "ends_at": "2026-11-01T21:00:00",
            "registration_deadline": "2026-10-30T18:00:00",
            "capacity": 2,
            "budget": "100.00",
        }
        payload.update(overrides)
        self.act_as(principal or self.leader1)
        response = self.post("/api/v1/activities", json=payload)
        assert response.status_code == 200, response.text
        return response.json()["data"]

    def approve(self, activity_id, *, comment="同意"):
        self.act_as(self.manager)
        response = self.post(
            f"/api/v1/activities/{activity_id}/review",
            json={"decision": "APPROVED", "comment": comment},
        )
        assert response.status_code == 200, response.text
        return response.json()["data"]

    def publish(self, activity_id):
        self.act_as(self.leader1)
        response = self.post(f"/api/v1/activities/{activity_id}/publish")
        assert response.status_code == 200, response.text
        return response.json()["data"]

    def approved_activity(self, *, publish=True, **overrides):
        activity = self.create_activity(**overrides)
        self.post(f"/api/v1/activities/{activity['id']}/submit")
        self.approve(activity["id"])
        if publish:
            return self.publish(activity["id"])
        return self.client.get(
            f"/api/v1/activities/{activity['id']}",
            headers={"Authorization": "Bearer test"},
        ).json()["data"]


@pytest.fixture
def env():
    instance = Env()
    try:
        yield instance
    finally:
        instance.close()


def test_create_activity_requires_club_leader_and_valid_schedule(env):
    activity = env.create_activity()
    assert activity["review_status"] == "DRAFT"
    assert activity["execution_status"] == "UNPUBLISHED"
    assert activity["club_id"] == 1
    assert activity["registration_count"] == 0
    assert activity["budget"] == 100.0

    env.act_as(env.leader2)
    forbidden = env.post("/api/v1/activities", json={"club_id": 1})
    assert forbidden.status_code == 422

    env.act_as(env.leader2)
    payload = {
        "club_id": 1,
        "title": "越权活动",
        "description": "描述",
        "location": "场地",
        "starts_at": "2026-11-01T19:00:00",
        "ends_at": "2026-11-01T21:00:00",
    }
    forbidden = env.post("/api/v1/activities", json=payload)
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == 40302

    env.act_as(env.leader1)
    invalid = env.post(
        "/api/v1/activities",
        json={**payload, "starts_at": "2026-11-01T21:00:00", "ends_at": "2026-11-01T19:00:00"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["code"] == 40002

    blank_title = env.post(
        "/api/v1/activities",
        json={**payload, "title": "   "},
    )
    assert blank_title.status_code == 422
    assert blank_title.json()["code"] == 40001


def test_update_submit_and_withdraw_state_machine(env):
    activity = env.create_activity()
    activity_id = activity["id"]

    response = env.patch(
        f"/api/v1/activities/{activity_id}",
        json={"title": "迎新晚会（修订）", "capacity": 3},
    )
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "迎新晚会（修订）"

    response = env.post(f"/api/v1/activities/{activity_id}/submit")
    assert response.status_code == 200
    assert response.json()["data"]["review_status"] == "PENDING"
    events = env.notifier.events("ACTIVITY_SUBMITTED")
    assert events and events[-1]["user_ids"] == [4]

    response = env.patch(f"/api/v1/activities/{activity_id}", json={"title": "待审核修改"})
    assert response.status_code == 409
    assert response.json()["code"] == 40901

    response = env.post(f"/api/v1/activities/{activity_id}/submit")
    assert response.status_code == 409

    response = env.post(f"/api/v1/activities/{activity_id}/withdraw")
    assert response.status_code == 200
    assert response.json()["data"]["review_status"] == "WITHDRAWN"

    response = env.patch(f"/api/v1/activities/{activity_id}", json={"title": "撤回后修订"})
    assert response.status_code == 200
    assert response.json()["data"]["title"] == "撤回后修订"


def test_review_requires_r03_and_records_result(env):
    activity = env.create_activity()
    activity_id = activity["id"]
    env.post(f"/api/v1/activities/{activity_id}/submit")

    env.act_as(env.student)
    response = env.post(
        f"/api/v1/activities/{activity_id}/review",
        json={"decision": "APPROVED", "comment": "同意"},
    )
    assert response.status_code == 403
    assert response.json()["code"] == 40301

    reviewed = env.approve(activity_id, comment="场地和时间符合要求")
    assert reviewed["review_status"] == "APPROVED"
    assert reviewed["review_comment"] == "场地和时间符合要求"
    assert reviewed["reviewed_by"] == 4
    assert env.notifier.events("ACTIVITY_REVIEWED")[-1]["user_ids"] == [2]

    response = env.post(
        f"/api/v1/activities/{activity_id}/review",
        json={"decision": "REJECTED", "comment": "重复审核"},
    )
    assert response.status_code == 409
    assert response.json()["code"] == 40901


def test_publish_then_student_registration_and_duplicate(env):
    activity = env.approved_activity(capacity=1)
    activity_id = activity["id"]
    assert activity["execution_status"] == "REGISTRATION_OPEN"

    env.act_as(env.student)
    response = env.post(f"/api/v1/activities/{activity_id}/registrations")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "REGISTERED"
    assert data["user"]["display_name"] == "学生一"

    duplicate = env.post(f"/api/v1/activities/{activity_id}/registrations")
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == 40902

    detail = env.get(f"/api/v1/activities/{activity_id}").json()["data"]
    assert detail["registration_count"] == 1
    assert detail["my_registration_status"] == "REGISTERED"

    assert env.notifier.events("ACTIVITY_REGISTRATION")[-1]["user_ids"] == [1]
    assert env.notifier.events("ACTIVITY_REGISTRATION_RECEIVED")[-1]["user_ids"] == [2]

    env.act_as(env.student2)
    full = env.post(f"/api/v1/activities/{activity_id}/registrations")
    assert full.status_code == 409
    assert full.json()["code"] == 40901
    assert "已满" in full.json()["message"]


def test_cancel_registration_allows_reregistration(env):
    activity = env.approved_activity(capacity=3)
    activity_id = activity["id"]
    env.act_as(env.student)
    env.post(f"/api/v1/activities/{activity_id}/registrations")

    response = env.delete(f"/api/v1/activities/{activity_id}/registrations/me")
    assert response.status_code == 200
    assert response.json()["data"] == {}

    response = env.delete(f"/api/v1/activities/{activity_id}/registrations/me")
    assert response.status_code == 409
    assert response.json()["code"] == 40901

    response = env.post(f"/api/v1/activities/{activity_id}/registrations")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "REGISTERED"
    assert env.notifier.events("ACTIVITY_REGISTRATION_CANCELLED")[-1]["user_ids"] == [2]


def test_registration_deadline_closes_registration_and_start_moves_to_progress(env):
    activity = env.create_activity(
        registration_deadline="2026-10-02T10:00:00",
        starts_at="2026-10-03T10:00:00",
        ends_at="2026-10-03T12:00:00",
    )
    activity_id = activity["id"]
    env.post(f"/api/v1/activities/{activity_id}/submit")
    env.approve(activity_id)
    env.publish(activity_id)

    env.clock.advance(days=1, hours=2)  # 2026-10-02 11:00
    detail = env.get(f"/api/v1/activities/{activity_id}").json()["data"]
    assert detail["execution_status"] == "REGISTRATION_CLOSED"

    env.act_as(env.student)
    blocked = env.post(f"/api/v1/activities/{activity_id}/registrations")
    assert blocked.status_code == 409
    assert "不接受报名" in blocked.json()["message"]

    env.clock.advance(days=1)  # 2026-10-03 11:00，活动已开始
    detail = env.get(f"/api/v1/activities/{activity_id}").json()["data"]
    assert detail["execution_status"] == "IN_PROGRESS"

    env.act_as(env.leader1)
    response = env.post(
        f"/api/v1/activities/{activity_id}/end", json={"summary": "活动顺利完成"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "ENDED"
    assert data["summary"] == "活动顺利完成"

    cancelled = env.post(
        f"/api/v1/activities/{activity_id}/cancel", json={"reason": "结束后取消"}
    )
    assert cancelled.status_code == 409
    assert cancelled.json()["code"] == 40901


def test_activity_cancel_notifies_registered_users_and_blocks_registration(env):
    activity = env.approved_activity(capacity=5)
    activity_id = activity["id"]
    env.act_as(env.student)
    env.post(f"/api/v1/activities/{activity_id}/registrations")

    env.act_as(env.leader1)
    response = env.post(
        f"/api/v1/activities/{activity_id}/cancel", json={"reason": "场地临时关闭"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "CANCELLED"
    assert data["cancellation_reason"] == "场地临时关闭"

    cancel_events = env.notifier.events("ACTIVITY_CANCELLED")
    assert cancel_events[-1]["user_ids"] == [1]
    assert "场地临时关闭" in cancel_events[-1]["content"]

    env.act_as(env.student)
    blocked = env.post(f"/api/v1/activities/{activity_id}/registrations")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == 40901

    env.act_as(env.leader2)
    forbidden = env.post(
        f"/api/v1/activities/{activity_id}/cancel", json={"reason": "越权取消"}
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == 40302


def test_cancel_and_end_reject_illegal_execution_states(env):
    activity = env.approved_activity()
    activity_id = activity["id"]

    env.act_as(env.leader1)
    response = env.post(f"/api/v1/activities/{activity_id}/end", json={})
    assert response.status_code == 409
    assert response.json()["code"] == 40901

    response = env.post(
        f"/api/v1/activities/{activity_id}/cancel", json={"reason": " "}
    )
    assert response.status_code == 400
    assert response.json()["code"] == 40002

    response = env.post(
        f"/api/v1/activities/{activity_id}/cancel", json={"reason": "临时取消"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["execution_status"] == "CANCELLED"

    again = env.post(
        f"/api/v1/activities/{activity_id}/cancel", json={"reason": "重复取消"}
    )
    assert again.status_code == 409
    assert again.json()["code"] == 40901


def test_visibility_and_registration_list_permissions(env):
    draft = env.create_activity(title="草稿活动")
    published = env.approved_activity(title="已发布活动")

    env.act_as(env.student)
    listed = env.get("/api/v1/activities").json()["data"]
    titles = {item["title"] for item in listed["items"]}
    assert "已发布活动" in titles
    assert "草稿活动" not in titles
    assert listed["total"] == 1

    forbidden = env.get(f"/api/v1/activities/{draft['id']}")
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == 40301

    env.act_as(env.manager)
    manager_list = env.get("/api/v1/activities").json()["data"]
    assert manager_list["total"] == 2

    env.act_as(env.admin)
    admin_list = env.get("/api/v1/activities").json()["data"]
    assert {item["title"] for item in admin_list["items"]} == {"已发布活动"}

    env.act_as(env.student)
    env.post(f"/api/v1/activities/{published['id']}/registrations")
    forbidden = env.get(f"/api/v1/activities/{published['id']}/registrations")
    assert forbidden.status_code == 403
    assert forbidden.json()["code"] == 40302

    env.act_as(env.leader1)
    roster = env.get(f"/api/v1/activities/{published['id']}/registrations")
    assert roster.status_code == 200
    data = roster.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["user"]["username"] == "student01"


def test_pagination_is_validated(env):
    response = env.get("/api/v1/activities?page=0")
    assert response.status_code == 422
    assert response.json()["code"] == 40001

    response = env.get("/api/v1/activities?page_size=101")
    assert response.status_code == 422
    assert response.json()["code"] == 40001

    response = env.get("/api/v1/activities?page=1&page_size=1")
    assert response.status_code == 200
    assert response.json()["data"]["page_size"] == 1


def test_publishing_requires_approval_and_open_registration(env):
    activity = env.create_activity()
    activity_id = activity["id"]

    response = env.post(f"/api/v1/activities/{activity_id}/publish")
    assert response.status_code == 409
    assert response.json()["code"] == 40901

    env.post(f"/api/v1/activities/{activity_id}/submit")
    env.approve(activity_id)

    env.clock.advance(days=40)  # 活动已开始
    env.act_as(env.leader1)
    response = env.post(f"/api/v1/activities/{activity_id}/publish")
    assert response.status_code == 409
    assert response.json()["code"] == 40901
