"""Member A 后端测试公共工具。

测试不连接 MySQL，也不使用 SQLite：Service 依赖的 Repository 函数由 monkeypatch
替换，FakeDb 只记录 add/commit/rollback 与通知查询结果，用来验证权限、状态转换
和事务内副作用。真实数据库链路由集成环境执行 migration/seed 后手工验证。
"""

import pytest

from app.core.permissions import Principal
from app.services import club_member_events
from tests.helpers import FakeDb


@pytest.fixture
def db():
    return FakeDb()


@pytest.fixture
def student():
    return Principal(user_id=1, username="student01", display_name="学生一", system_roles={"R01"})


@pytest.fixture
def leader():
    return Principal(
        user_id=2,
        username="leader01",
        display_name="负责人一",
        system_roles={"R01"},
        club_leader_ids={1},
    )


@pytest.fixture
def manager():
    return Principal(
        user_id=9,
        username="manager01",
        display_name="管理人员",
        system_roles={"R01", "R03"},
    )


@pytest.fixture
def event_calls(monkeypatch):
    calls = {"notifications": [], "audits": []}

    def notify_managers(database, **kwargs):
        calls["notifications"].append(("managers", kwargs))

    def notify_club_leaders(database, club_id, **kwargs):
        calls["notifications"].append(("club_leaders", club_id, kwargs))

    def notify_user(database, user_id, **kwargs):
        calls["notifications"].append(("user", user_id, kwargs))

    def record_audit(database, **kwargs):
        calls["audits"].append(kwargs)

    monkeypatch.setattr(club_member_events, "notify_managers", notify_managers)
    monkeypatch.setattr(club_member_events, "notify_club_leaders", notify_club_leaders)
    monkeypatch.setattr(club_member_events, "notify_user", notify_user)
    monkeypatch.setattr(club_member_events, "record_audit", record_audit)
    return calls
