"""M01/M04/M05/M06/M07 端到端联调脚本（需要已启动后端 + MySQL + seed）。

用法：
    cd ruanjian/backend
    python ../docs/integration/smoke_m01_m07.py

默认地址 http://127.0.0.1:8000/api/v1，可通过环境变量 API_BASE 覆盖。
脚本会创建带时间戳的测试账号、活动、经费和通知数据，不会删除数据；仅用于本地验证。
M02/M03 的联调脚本见 docs/member-a/integration/smoke_m02_m03.py。
"""

import os
import sys
from datetime import datetime, timedelta

import httpx

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api/v1")
CLIENT = httpx.Client(base_url=BASE, timeout=20)
PASSED = []


def login(username, password):
    response = CLIENT.post("/auth/login", json={"username": username, "password": password})
    body = response.json()
    if response.status_code >= 400 or body.get("code") != 0:
        raise RuntimeError(f"登录失败 {username}: {body}")
    return body["data"]["access_token"]


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def call(method, path, token, expect=200, **kwargs):
    response = CLIENT.request(method, path, headers=headers(token), **kwargs)
    body = response.json() if response.content else {}
    if expect is not None and response.status_code != expect:
        raise RuntimeError(f"{method} {path} 期望 {expect}，实际 {response.status_code}: {body}")
    if expect is not None and response.status_code < 400 and body.get("code") != 0:
        raise RuntimeError(f"{method} {path} 业务失败: {body}")
    return body


def ok(label):
    PASSED.append(label)
    print(f"PASS {label}")


def main():
    suffix = datetime.now().strftime("%H%M%S")
    admin = login("admin01", "Admin123!")
    student = login("student01", "Student123!")
    leader = login("leader01", "Leader123!")
    manager = login("manager01", "Manager123!")
    ok("四个测试账号真实登录")

    if call("GET", "/health", admin)["data"]["database"] != "up":
        raise RuntimeError("health 数据库状态不是 up")
    ok("health 连接真实 MySQL")

    # ---------------- M01 FR-23 ----------------
    accounts = call("GET", "/accounts", admin, params={"page": 1, "page_size": 100})["data"]
    ok(f"M01 账号列表（{accounts['total']} 个账号）")
    call("GET", "/accounts", student, expect=403)
    ok("M01 非 R04 访问账号列表被拒绝 403")

    created = call(
        "POST", "/accounts", admin,
        json={"username": f"m01smoke{suffix}", "display_name": "M01 冒烟账号", "password": "Smoke1234!"},
    )["data"]
    account_id = created["user_id"]
    ok(f"M01 创建账号 #{account_id}（自动 R01）")
    if created["system_roles"] != ["R01"]:
        raise RuntimeError(f"新账号系统角色异常: {created['system_roles']}")

    updated = call(
        "PATCH", f"/accounts/{account_id}", admin,
        json={"display_name": "M01 冒烟账号-禁用", "status": "DISABLED"},
    )["data"]
    if updated["status"] != "DISABLED":
        raise RuntimeError("账号停用未生效")
    ok("M01 账号停用生效")
    call("PATCH", f"/accounts/{account_id}", admin, json={"status": "NORMAL"})
    ok("M01 账号恢复启用")

    call("POST", f"/accounts/{account_id}/role-assignments", admin, json={"role_code": "R03"})
    listing = call("GET", "/accounts", admin, params={"page": 1, "page_size": 100})["data"]["items"]
    target = next(item for item in listing if item["user_id"] == account_id)
    if "R03" not in target["system_roles"]:
        raise RuntimeError(f"授予 R03 后列表未体现: {target}")
    ok("M01 授予 R03")
    call("DELETE", f"/accounts/{account_id}/role-assignments/R03", admin)
    ok("M01 撤销 R03")

    clubs = call("GET", "/clubs", admin, params={"page": 1, "page_size": 100})["data"]["items"]
    grant_club_id = clubs[0]["id"]
    call("POST", f"/accounts/{account_id}/role-assignments", admin, json={"role_code": "R02", "club_id": grant_club_id})
    ok(f"M01 授予社团 #{grant_club_id} 的 R02")
    call("DELETE", f"/accounts/{account_id}/club-role-assignments/{grant_club_id}", admin)
    ok("M01 撤销社团 R02")

    call("POST", f"/accounts/{account_id}/role-assignments", admin, json={"role_code": "R02"}, expect=400)
    ok("M01 授予 R02 缺少 club_id 被拒绝 400")

    # ---------------- M04 ----------------
    leader_me = call("GET", "/auth/me", leader)["data"]
    if not leader_me["club_authorizations"]:
        raise RuntimeError("leader01 没有 R02 社团授权")
    club_id = leader_me["club_authorizations"][0]["club_id"]
    student_id = call("GET", "/auth/me", student)["data"]["user_id"]
    starts = datetime.now() + timedelta(days=7)
    payload = {
        "club_id": club_id,
        "title": f"M04 冒烟活动 {suffix}",
        "description": "端到端冒烟用虚构活动",
        "location": "测试教室",
        "starts_at": starts.isoformat(timespec="seconds"),
        "ends_at": (starts + timedelta(hours=2)).isoformat(timespec="seconds"),
        "registration_deadline": (starts - timedelta(days=1)).isoformat(timespec="seconds"),
        "capacity": 20,
        "budget": "100.00",
    }
    activity = call("POST", "/activities", leader, json=payload)["data"]
    activity_id = activity["id"]
    ok(f"M04 创建活动草稿 #{activity_id}")
    call("POST", f"/activities/{activity_id}/submit", leader)
    ok("M04 提交活动审核")
    call("POST", f"/activities/{activity_id}/review", manager, json={"decision": "APPROVED", "comment": "冒烟通过"})
    ok("M04 R03 审核通过")
    call("POST", f"/activities/{activity_id}/publish", leader)
    ok("M04 发布活动")
    call("POST", f"/activities/{activity_id}/registrations", student)
    ok("M04 学生报名")
    call("DELETE", f"/activities/{activity_id}/registrations/me", student)
    ok("M04 学生取消报名")

    # ---------------- M05 ----------------
    record = call(
        "POST", "/finance-records", leader, expect=201,
        json={
            "club_id": club_id, "record_type": "EXPENSE", "amount": "35.50",
            "occurred_on": datetime.now().date().isoformat(),
            "description": "冒烟支出", "voucher_reference": None,
        },
    )["data"]
    ok(f"M05 登记经费 #{record['id']}")
    summary = call("GET", "/finance-records/summary", manager, params={"club_id": club_id})["data"]
    if "expense_total" not in summary:
        raise RuntimeError(f"经费汇总字段异常: {summary}")
    ok("M05 经费汇总")

    # ---------------- M06 ----------------
    notice = call(
        "POST", "/notifications/management", manager,
        json={"title": f"冒烟通知 {suffix}", "content": "端到端冒烟", "target_type": "USERS",
              "user_ids": [student_id], "role_codes": [], "club_ids": []},
    )["data"]
    ok(f"M06 发布管理通知（{notice['created_count']} 条）")
    inbox = call("GET", "/notifications", student)["data"]
    if inbox["total"] < 1:
        raise RuntimeError("学生通知列表为空")
    ok(f"M06 学生通知列表（{inbox['total']} 条）")
    first = inbox["items"][0]
    call("POST", f"/notifications/{first['id']}/read", student)
    ok("M06 标记已读")

    # ---------------- M07 ----------------
    report = call("GET", "/reports/summary", manager)["data"]
    for field in ("club_count", "member_count", "activity_count", "registration_count"):
        if field not in report:
            raise RuntimeError(f"统计缺少字段 {field}")
    ok("M07 综合统计（社团/成员/活动/报名）")
    csv_response = CLIENT.get("/reports/export", headers=headers(manager))
    if csv_response.status_code != 200 or "text/csv" not in csv_response.headers.get("content-type", ""):
        raise RuntimeError(f"CSV 导出异常: {csv_response.status_code} {csv_response.headers.get('content-type')}")
    ok("M07 经费 CSV 导出")
    audit = call("GET", "/audit-logs", admin)["data"]
    if audit["total"] < 1:
        raise RuntimeError("审计日志为空")
    ok(f"M07 审计日志查询（{audit['total']} 条）")

    print(f"\nALL PASS（{len(PASSED)} 项）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"\nFAIL: {exc}")
        sys.exit(1)
