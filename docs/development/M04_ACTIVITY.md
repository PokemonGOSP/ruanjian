# M04 活动管理实现说明（Member B）

> 需求基线：`REQUIREMENTS_BASELINE_V1_1.md` FR-11～FR-16（含 CR-03）
> API 契约：`docs/api/API_CONTRACT_V0_1.md` 第 7 节
> 实现状态：`IMPLEMENTED`

## 1. 范围

M04 覆盖活动申请创建、编辑、提交、撤回、R03 审核、发布、报名/取消报名、报名名单、
执行阶段取消与结束归档。审核状态 `ReviewStatus` 与执行状态 `ActivityExecutionStatus`
保持两个独立字段，不合并、不混用“撤回”和“取消”。

不实现：签到、候补、退款、场地释放、票务、多级审核、外部通知渠道。

M07-B（活动/报名统计）在 V0.1 API Contract 中没有独立 endpoint；`/reports/summary` 属 M07，
由 Member C 统一实现。M04 已提供有效报名人数、报名名单和活动状态数据，可直接供 M07 聚合；
新增独立统计路径需先由负责人补充契约，本分支不擅自扩展。

## 2. 分层与文件

```text
frontend/src/views/ActivitiesView.vue     活动管理页面（列表/表单/审核/报名/归档）
frontend/src/api/activities.js             活动 API 封装
backend/app/api/v1/activities.py           Router：HTTP 契约、分页参数、统一响应
backend/app/services/activity_service.py   Service：权限、状态转换、事务、业务通知
backend/app/repositories/activity_repository.py  Repository：查询与加锁
backend/app/services/notification_service.py     FR-19 站内通知写入（仅写入，查询归 M06）
backend/app/schemas/business.py            M04 请求 schema
backend/app/schemas/activity.py            M04 响应 schema
backend/tests/test_activities.py           M04 自动化测试
```

## 3. 状态机

### 3.1 审核状态（R02 提交、R03 审核）

| 当前 | 操作 | 结果 | 约束 |
|---|---|---|---|
| 草稿 / 已撤回 | PATCH 编辑 | 状态不变 | 仅目标社团 R02；时间顺序合法 |
| 草稿 / 已撤回 | 提交 | 待审核 | 活动结束时间必须晚于当前时间 |
| 待审核 | 撤回 | 已撤回 | 仅目标社团 R02 |
| 待审核 | 审核通过 | 已通过 | 仅 R03；执行状态初始化为未发布 |
| 待审核 | 审核驳回 | 已驳回 | 仅 R03；保存意见，不产生获准活动 |
| 已通过 / 已驳回 | 编辑、提交、撤回 | 拒绝 | HTTP 409 / 40901 |

已驳回记录不直接复用；如需再次申报，创建新的活动申请。

### 3.2 执行状态

| 当前 | 操作/触发 | 结果 |
|---|---|---|
| 未发布 | R02 发布（已通过、未开始、未过报名截止） | 报名中 |
| 报名中 | 到达 `registration_deadline`（系统自动） | 报名截止 |
| 报名中 / 报名截止 | 到达 `starts_at`（系统自动） | 进行中 |
| 未发布 / 报名中 / 报名截止 / 进行中 | R02 取消（必填原因） | 已取消 |
| 报名截止 / 进行中 | R02 结束并归档 | 已结束 |
| 已结束 / 已取消 | 再次取消或结束 | 拒绝（409 / 40901） |

时间驱动的状态推进在读取详情/列表、发布、报名、取消报名、结束时按当前时间计算并落库；
“结束”仍由 R02 显式操作，以便填写活动总结。

## 4. 业务规则

- **资源归属**：所有 R02 操作通过 `Principal.leads_club(club_id)` 校验目标社团，不使用全局用户角色；
  跨社团操作返回 403 / 40302。R03 只执行审核，R04 不参与业务审核。
- **创建/编辑**：`starts_at < ends_at`；`registration_deadline < starts_at`；容量 ≥ 1；预算 ≥ 0。
- **发布**：必须已通过审核、执行状态为未发布、当前时间早于开始时间和报名截止时间。
- **报名**：仅执行状态为报名中；未过报名截止；未重复报名；未超过容量；已取消的报名可重新报名，
  复用同一条报名记录（唯一约束 `(activity_id, user_id)`）。
- **取消报名**：仅报名本人；报名已取消返回 40901；活动已结束或已取消后不允许取消报名。
- **取消活动**：必须有非空原因；取消后不接受新报名；已报名用户保留报名记录用于历史统计；
  通过 FR-19 向所有“已报名”用户写入站内通知。
- **结束活动**：仅报名截止/进行中可结束；可填写总结；结束后不能取消。
- **可见范围**：R03 可见全部；R02 可见本社团全部活动 + 其他社团已通过且已发布活动；
  其他登录用户仅可见已通过且已发布（未发布除外）的活动。

## 5. 通知事件（FR-19 记录）

| event_type | 触发 | 收件人 |
|---|---|---|
| `ACTIVITY_SUBMITTED` | 活动提交审核 | 所有有效 R03 用户 |
| `ACTIVITY_REVIEWED` | 审核通过/驳回 | 活动创建人 |
| `ACTIVITY_REGISTRATION` | 报名成功 | 报名学生 |
| `ACTIVITY_REGISTRATION_RECEIVED` | 有新报名 | 活动创建人（非本人报名时） |
| `ACTIVITY_REGISTRATION_CANCELLED` | 学生取消报名 | 活动创建人（非本人操作时） |
| `ACTIVITY_CANCELLED` | 活动取消 | 所有已报名用户 |

通知与业务状态在同一事务中提交；M06 的查询/已读/管理通知 API 仍由 Member C 实现。

## 6. API 扩展字段

在契约路径和 method 不变的前提下，M04 响应增加以下向后兼容字段：

- `Activity.registration_count`：当前有效报名人数；
- `Activity.my_registration_status`：当前登录用户的报名状态（`REGISTERED` / `CANCELLED` / `null`）；
- 报名名单条目增加 `user: {id, username, display_name}`，用于 R02 查看名单。

分页参数 `page ≥ 1`、`1 ≤ page_size ≤ 100`，非法值返回 HTTP 422 / 40001。

## 7. 验证

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check app tests

cd ..\frontend
npm.cmd run build
```

本机结果：

- `pytest`：15 passed（M04 新增 11 个用例，覆盖权限、状态机、期限/容量、通知和分页）；
- `ruff`：M04 新增/修改文件无告警（仓库既有文件的历史告警未处理）；
- `vite build`：通过。

测试使用内存 Repository / Notifier 替身，不依赖 MySQL，也未把工程配置改为 SQLite。
2026-10-31 已在 MySQL 8.4.11 上完成 migration、seed 和活动全流程接口联调
（见 `docs/integration/smoke_m01_m07.py`）；Playwright 已覆盖登录、角色可见性与模块导航，
活动逐项点击流程尚未纳入浏览器自动化。

## 8. 与现有数据模型的关系

M04 未新增表、未修改 Alembic migration、未修改公共枚举或认证/JWT。使用既有
`activities`（审核状态、执行状态、取消原因、总结）与 `activity_registrations`
（报名状态、报名/取消时间）表；通知写入既有 `notifications` 表。
