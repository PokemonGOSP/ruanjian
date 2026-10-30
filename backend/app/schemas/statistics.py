"""M07-A 社团/成员统计的响应 Schema。

M07-A 只提供查询服务，不新增公共 URL；由 M07 的 `/reports/summary` 组合返回，
详见 `docs/M07A_CLUB_MEMBER_STATISTICS.md`。
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ClubStatisticsItem(BaseModel):
    club_id: int
    club_name: str
    active_member_count: int
    exited_member_count: int
    pending_membership_application_count: int
    annual_review_status: Literal["DRAFT", "PENDING", "APPROVED", "REJECTED", "WITHDRAWN"] | None = None


class ClubMemberStatisticsData(BaseModel):
    scope: Literal["ALL", "OWN_CLUBS"]
    review_year: int
    total_clubs: int
    total_active_members: int
    total_active_memberships: int
    total_memberships: int
    total_pending_membership_applications: int
    items: list[ClubStatisticsItem]
    generated_at: datetime
