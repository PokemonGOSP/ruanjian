# M07-A 社团/成员统计

> 所属：M07 统计与审计中的社团/成员部分（`ENGINEERING_SKELETON_V0_1_FINAL.md` 将 M07-A 分给成员 A）。
> 约束：`docs/api/API_CONTRACT_V0_1.md` 只定义 `/reports/summary` 和 `/reports/export`，**没有为 M07-A 定义独立 URL**。因此本交付不新增公共路由，只提供可被 M07 组合的查询 Service。

## 1. 服务位置与签名

```python
from app.services.club_member_statistics import club_member_statistics

data = club_member_statistics(
    db,
    principal,
    club_id=None,       # 可选；R02 必须是本人负责社团，R03 可任意
    review_year=None,   # 可选；默认当前自然年
)
```

返回 `dict`，可直接交给 `app/schemas/statistics.py` 的 `ClubMemberStatisticsData` 校验，也可作为 `/reports/summary` 的一个子对象。

## 2. 权限

| 角色 | 范围 |
|---|---|
| R03 | 全部社团；可按 `club_id` 过滤 |
| R02 | 仅 `principal.club_leader_ids` 中的社团；传入其他 `club_id` 返回 `40302` |
| R01 / R04 | `40301`（FR-21 角色为 R02、R03） |

权限在 Service 内再次校验，不依赖调用方（例如 `/reports/summary`）是否已做过滤，避免组合时越权。

## 3. 统计口径

| 字段 | 口径 |
|---|---|
| `scope` | `ALL`（R03）或 `OWN_CLUBS`（R02） |
| `review_year` | 统计年审状态所用年度 |
| `total_clubs` | 权限范围内的社团数 |
| `total_active_members` | 范围内 `ACTIVE` 成员关系的**去重用户数** |
| `total_active_memberships` | 范围内 `ACTIVE` 成员关系条数（同一用户可属于多个社团） |
| `total_memberships` | 范围内 `ACTIVE + EXITED` 成员关系条数 |
| `total_pending_membership_applications` | 范围内 `PENDING` 成员申请数 |
| `items[].active_member_count` | 该社团 `ACTIVE` 成员关系数 |
| `items[].exited_member_count` | 该社团 `EXITED` 成员关系数 |
| `items[].pending_membership_application_count` | 该社团 `PENDING` 成员申请数 |
| `items[].annual_review_status` | 该社团在 `review_year` 的年审状态；无记录为 `null` |
| `generated_at` | 查询时间 |

说明：

- 成员关系是“用户—社团”业务关系，不是全局角色；统计不会把 R02 当作用户角色计数。
- 年审状态来自 `annual_review_applications` 的 `(club_id, review_year)` 唯一记录。
- 统计是只读查询，不写通知/审计；FR-21 的查询本身不要求审计（FR-22 的关键操作审计由 M07 决定）。

## 4. 响应示例

```json
{
  "scope": "ALL",
  "review_year": 2026,
  "total_clubs": 3,
  "total_active_members": 12,
  "total_active_memberships": 15,
  "total_memberships": 18,
  "total_pending_membership_applications": 2,
  "items": [
    {
      "club_id": 1,
      "club_name": "星河读书社",
      "active_member_count": 6,
      "exited_member_count": 1,
      "pending_membership_application_count": 1,
      "annual_review_status": "APPROVED"
    }
  ],
  "generated_at": "2026-10-26T22:00:00"
}
```

## 5. 与 `/reports/summary` 的组合方式

M07 owner 在 `app/api/v1/reports.py` 实现 `/reports/summary` 时，可以：

```python
from app.services.club_member_statistics import club_member_statistics

@router.get("/reports/summary", response_model=ApiResponse[ReportSummary])
def summary(principal: CurrentPrincipal, db: DbSession, ...):
    club_member = club_member_statistics(db, principal, club_id=club_id, review_year=review_year)
    return _success({
        "club_member": club_member,
        # ... 活动/报名/经费统计
    })
```

需要一个可直接粘贴的示例见 [`../integration/reports_m07a_snippet.py`](../integration/reports_m07a_snippet.py)。

**不要**直接把 `club_member_statistics` 暴露成新的 `/reports/club-members` 路由：

- 契约没有该 URL；
- 新增 URL 属于契约变更，必须由负责人按 `docs/api/API_CONTRACT_V0_1.md` 第 11 节处理；
- 本交付保持“Service 先行、路由由 M07 owner 统一组合”的边界。

## 6. 测试

测试分为两层：

1. `backend/tests/test_m07a_statistics.py`（4 个单元测试）：R01 无权限、R02 越权、R02 范围、R03 全量；
2. 2026-10-30 真实 MySQL 8.4.11 验证：直接调用 `club_member_statistics()`，确认 `GROUP BY`、`COUNT(DISTINCT)`、年审状态关联可执行：
   - R03：`clubs=5 active=4 memberships=8 pending=0`；
   - R02：`clubs=2`，只包含负责的 Club 5、Club 4；
   - R01：`40301`。

证据见 [`REAL_DB_AND_BROWSER_ACCEPTANCE.md`](REAL_DB_AND_BROWSER_ACCEPTANCE.md) 第 3.6 节。
