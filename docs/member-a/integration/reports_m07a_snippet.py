"""示例：M07 owner 在 /reports/summary 中组合 M07-A 社团/成员统计。

本文件不参与应用导入，只是交付给负责人的集成参考。复制到 reports.py 时请按
现有 ReportSummary Schema 调整字段名，不要改变 API Contract 的 URL/method。
"""

from sqlalchemy.orm import Session

from app.core.permissions import Principal
from app.services.club_member_statistics import club_member_statistics


def build_club_member_report_section(
    db: Session,
    principal: Principal,
    *,
    club_id: int | None = None,
    review_year: int | None = None,
) -> dict:
    """返回 M07-A 统计子对象；权限和范围由 Service 再次校验。"""
    return club_member_statistics(
        db,
        principal,
        club_id=club_id,
        review_year=review_year,
    )


# 在 reports.py 的 summary handler 中：
#
# data = {
#     "club_member": build_club_member_report_section(
#         db, principal, club_id=club_id, review_year=review_year
#     ),
#     "activities": ...,
#     "registrations": ...,
#     "finance": ...,
# }
# return {"code": 0, "message": "success", "data": data}
