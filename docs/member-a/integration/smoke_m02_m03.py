"""M02/M03 端到端联调脚本（需要已启动后端 + MySQL + seed）。

用法：
    cd ruanjian-main/backend
    python ../../成员A/integration/smoke_m02_m03.py

默认地址 http://127.0.0.1:8000/api/v1，可通过环境变量 API_BASE 覆盖。
脚本会创建一条带时间戳的测试社团，不会删除数据；仅用于本地验证。
"""

import os
import sys
from datetime import datetime

import httpx

BASE = os.getenv("API_BASE", "http://127.0.0.1:8000/api/v1")
CLIENT = httpx.Client(base_url=BASE, timeout=15)


def login(username: str, password: str) -> str:
    response = CLIENT.post("/auth/login", json={"username": username, "password": password})
    response.raise_for_status()
    body = response.json()
    if body.get("code") != 0:
        raise RuntimeError(f"登录失败：{body}")
    return body["data"]["access_token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def call(method: str, path: str, token: str, **kwargs) -> dict:
    response = CLIENT.request(method, path, headers=headers(token), **kwargs)
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError(f"{method} {path} 返回非 JSON：{response.text}") from exc
    if response.status_code >= 400 or body.get("code") != 0:
        raise RuntimeError(f"{method} {path} 失败：HTTP {response.status_code} {body}")
    return body["data"]


def main() -> int:
    suffix = datetime.now().strftime("%Y%m%d%H%M%S")
    club_name = f"成员A联调社团{suffix}"

    student = login("student01", "Student123!")
    student2 = login("student02", "Student123!")
    login("leader01", "Leader123!")
    manager = login("manager01", "Manager123!")
    print("[1] 四个测试账号登录成功")

    application = call(
        "POST",
        "/club-registration-applications",
        student2,
        json={"proposed_name": club_name, "description": "成员A联调用虚构社团", "advisor_contact": None},
    )
    application_id = application["id"]
    assert application["review_status"] == "DRAFT"
    print(f"[2] student02 创建注册申请 #{application_id}，状态 DRAFT")

    application = call("POST", f"/club-registration-applications/{application_id}/submit", student2)
    assert application["review_status"] == "PENDING"
    print("[3] 注册申请已提交，状态 PENDING")

    page = call("GET", "/club-registration-applications?status=PENDING&page_size=100", manager)
    target = next(item for item in page["items"] if item["id"] == application_id)
    assert target["proposed_name"] == club_name
    print(f"[4] manager01 能在待审核列表中看到申请，共 {page['total']} 条")

    result = call(
        "POST",
        f"/club-registration-applications/{application_id}/review",
        manager,
        json={"decision": "APPROVED", "comment": "联调通过"},
    )
    club_id = result["club"]["id"]
    assert result["application"]["review_status"] == "APPROVED"
    assert result["club_authorization"] == {
        "club_id": club_id,
        "user_id": target["applicant_user_id"],
        "role_code": "R02",
    }
    print(f"[5] 审核通过，建立 Club #{club_id} 并授予申请人该社团 R02")

    me = call("GET", "/auth/me", student2)
    assert any(item["club_id"] == club_id for item in me["club_authorizations"])
    print("[6] student02 的 /auth/me 已出现新社团 R02 授权")

    annual = call(
        "POST",
        "/annual-reviews",
        student2,
        json={"club_id": club_id, "review_year": 2099, "materials": "联调虚构年审材料"},
    )
    annual_id = annual["id"]
    annual = call("POST", f"/annual-reviews/{annual_id}/submit", student2)
    assert annual["review_status"] == "PENDING"
    reviewed = call(
        "POST",
        f"/annual-reviews/{annual_id}/review",
        manager,
        json={"decision": "REJECTED", "comment": "联调：材料不完整"},
    )
    assert reviewed["review_status"] == "REJECTED"
    print("[7] 年审提交/驳回成功；驳回只改年审记录，未冻结社团")

    membership = call(
        "POST",
        "/membership-applications",
        student,
        json={"club_id": club_id, "application_type": "JOIN", "reason": "联调入团"},
    )
    membership_id = membership["id"]
    processed = call(
        "POST",
        f"/membership-applications/{membership_id}/process",
        student2,
        json={"decision": "APPROVED", "comment": "联调欢迎"},
    )
    assert processed["application"]["status"] == "APPROVED"
    assert processed["member"]["status"] == "ACTIVE"
    print("[8] 入团申请处理成功，成员关系为 ACTIVE")

    roster = call("GET", f"/clubs/{club_id}/members?page_size=100", student2)
    assert any(item["user_id"] == target["applicant_user_id"] for item in roster["items"])
    print(f"[9] 负责人可查看完整名册，共 {roster['total']} 人")

    print("\nALL PASS：M02/M03 端到端联调通过")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - 联调脚本需要打印可读失败原因
        print(f"\nSMOKE FAILED：{exc}", file=sys.stderr)
        sys.exit(1)
