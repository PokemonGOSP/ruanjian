# 成员 C 实现说明：M05 / M06 / M07

> 需求基线：`REQUIREMENTS_BASELINE_V1_1.md`
> API 契约：`docs/api/API_CONTRACT_V0_1.md`
> 范围：FR-17～FR-22 的实现与验证；FR-23 仅提供审计写入/查询接入点，不实现账号授权
> 实现人：成员 C

## 1. 交付范围

| 模块 | FR | 已实现内容 |
|---|---|---|
| M05 经费记录 | FR-17、FR-18 | 登记、修改、作废、列表查询、汇总；关联活动校验；审计 |
| M06 通知中心 | FR-19、FR-20 | 本人通知列表、单条已读、全部已读、R03 管理通知发布；FR-19 通用通知 service |
| M07 统计与审计 | FR-21、FR-22 | 综合统计、经费 CSV 导出、R04 审计日志查询 |

未实现且明确排除：经费审批/报销/支付/财务结算、邮件/短信/企业微信等外部通知、WebSocket、真实 MySQL 以外的替代数据库。

## 2. 端点与权限

| 端点 | FR | 允许角色 | 说明 |
|---|---|---|---|
| `GET /finance-records/summary` | FR-18 | 目标社团 R02；R03 全部 | 收入/支出/结余/有效与作废计数 |
| `POST /finance-records` | FR-17 | 目标社团 R02 | 新建即 `ACTIVE` |
| `GET /finance-records` | FR-18 | 目标社团 R02；R03 全部 | 分页 + 过滤 |
| `PATCH /finance-records/{id}` | FR-17 | 目标社团 R02 | 仅 `ACTIVE` 可改 |
| `POST /finance-records/{id}/void` | FR-17 | 目标社团 R02 | 必填原因；保留原记录 |
| `GET /notifications` | FR-19 | 当前用户本人 | 只能看到本人通知 |
| `POST /notifications/{id}/read` | FR-19 | 收件人本人 | 未读 → 已读，幂等 |
| `POST /notifications/read-all` | FR-19 | 当前用户本人 | 全部未读 → 已读 |
| `POST /notifications/management` | FR-20 | R03 | 按用户/角色/社团范围发布 |
| `GET /reports/summary` | FR-21 | 本社团 R02；R03 全部 | 综合统计 |
| `GET /reports/export` | FR-21 | 本社团 R02；R03 全部 | 仅 CSV |
| `GET /audit-logs` | FR-22 | R04 | 分页 + 过滤 |

权限实现：

- R02 使用 `club_role_assignments` 中针对目标 `club_id` 的有效授权，不读取全局 `users.role`。
- R03 默认访问系统内全部社团业务记录，不引入学院、部门或辖区模型。
- R04 仅访问审计查询，不参与业务审核。
- 跨社团 R02 访问返回 `40302`；缺少 R03/R04 返回 `40301`。

## 3. M05 业务规则

1. `record_type` 只能是 `INCOME` 或 `EXPENSE`；`amount > 0`，最多 12 位、2 位小数。
2. `activity_id` 可选；如填写，活动必须存在且属于同一 `club_id`，否则 `40002`。
3. 修改只允许调整活动、类型、金额、发生日期、说明和凭证信息；不能修改 `club_id` 或 `status`。`record_type`、`amount`、`occurred_on`、`description` 显式传 `null` 返回 `40002`。
4. 只有 `ACTIVE` 记录可修改或作废；已作废记录再次作废返回 `40901`。
5. 作废必须填写原因，写入 `voided_by`、`void_reason` 并保留原记录，不物理删除。
6. 汇总只把 `ACTIVE` 记录计入收入/支出/结余，另返回有效记录数与已作废数。
7. 创建、修改、作废均写入 `audit_logs`，动作分别为 `FINANCE_RECORD_CREATED`、`FINANCE_RECORD_UPDATED`、`FINANCE_RECORD_VOIDED`。
8. R02 未指定 `club_id` 时聚合其全部有效社团；指定时必须为本人负责社团；R03 未指定时聚合全部社团。

## 4. M06 业务规则

1. 通知列表仅查询 `recipient_user_id = 当前用户` 的记录；`read_status` 可选过滤。
2. 标记已读仅允许收件人本人；通知不存在返回 `40401`，非本人返回 `40301`。
3. 管理通知 `target_type` 与目标列表必须匹配，禁止混合：
   - `USERS`：`user_ids`；
   - `ROLES`：`role_codes`（`R02` 解析为全部有效社团负责人授权）；
   - `CLUBS`：`club_ids`（有效成员 + 有效 R02 负责人）。
4. 接收人去重；目标不存在或无接收人返回 `40002`。
5. 管理通知写入 `event_type = MANAGEMENT_NOTICE`，并记录审计 `MANAGEMENT_NOTIFICATION_PUBLISHED`。
6. 仅站内通知，不新增外部渠道。

### 4.1 FR-19 供成员 A/B 接入的通知 service

```python
from app.services.notification_service import notify, notify_many

# 单个用户
notify(
    db,
    recipient_user_id=user_id,
    title="活动已取消",
    content="您报名的活动已取消，原因：……",
    event_type="ACTIVITY_CANCELLED",
    related_type="activity",
    related_id=activity.id,
)

# 多个用户（内部会去重排序）
notify_many(
    db,
    recipient_user_ids=user_ids,
    title="审核结果",
    content="您的申请已通过。",
    event_type="REVIEW_RESULT",
    related_type="activity",
    related_id=activity.id,
)
```

调用方与业务状态变更放在同一事务中提交；不要在通知 service 内单独 `commit`。

## 5. M07 业务规则

### 5.1 综合统计

- 过滤：`club_id`、`date_from`、`date_to`。
- 返回：社团数、有效成员数、活动数、有效报名数、活动审核/执行状态分布、经费收入/支出/结余/作废数。
- 日期口径：
  - 活动按 `activities.starts_at`；
  - 经费按 `finance_records.occurred_on`；
  - 报名按所属活动开始时间；
  - 成员数为当前 `ACTIVE` 成员，不受日期过滤影响。
- 状态分布对全部固定枚举值补零，便于前端稳定展示。

### 5.2 CSV 导出

- 仅支持 `format=csv`，其他格式返回 `40001`。
- 内容为经费明细，前置汇总头（社团范围、收入、支出、结余、有效/作废数、生成时间）。
- 使用 UTF-8 BOM + CRLF，便于 Excel 打开。
- 对以 `= + - @`、制表符或回车开头的文本单元格加 `'` 前缀，防止 CSV 公式注入。
- 权限范围与经费列表一致；R02 只导出本人社团，R03 导出全部或指定社团。

### 5.3 审计日志

- 仅 R04 可查询。
- 过滤：`actor_user_id`、`action`、`resource_type`、`date_from`、`date_to`。
- `detail` 返回解析后的 JSON；无法解析时返回原始文本。
- 审计写入统一使用：

```python
from app.services.audit_service import record_audit

record_audit(
    db,
    actor_user_id=principal.user_id,
    action="ACTIVITY_CANCELLED",
    resource_type="activity",
    resource_id=activity.id,
    detail={"reason": reason},
    ip_address=request_ip(request),
)
```

负责人实现 FR-23 授权变更、成员 A/B 实现审核/取消时，可按同一模式写入，R04 的审计查询即可覆盖。

## 6. 错误码

| code | HTTP | 场景 |
|---|---:|---|
| 40001 | 422 | 参数校验失败（金额、类型、分页等） |
| 40002 | 400 | 业务规则不满足（活动不属于社团、空更新、无效通知目标） |
| 40301 | 403 | 缺少 R03/R04 等系统角色 |
| 40302 | 403 | 缺少目标社团 R02 |
| 40401 | 404 | 经费记录、通知或社团不存在 |
| 40901 | 409 | 已作废记录再修改/再作废 |
| 50000 | 500 | 未预期服务端错误 |
| 50001 | 503 | 数据库暂不可用 |

## 7. 文件清单

后端：

- `app/api/v1/finance.py`
- `app/api/v1/notifications.py`
- `app/api/v1/reports.py`
- `app/schemas/finance.py`
- `app/schemas/notification.py`
- `app/schemas/report.py`
- `app/services/club_scope.py`
- `app/services/audit_service.py`
- `app/services/notification_service.py`
- `app/services/finance_service.py`
- `app/services/report_service.py`
- `app/core/datetime_utils.py`
- `app/core/exceptions.py`（最小修复：校验错误序列化）
- `tests/conftest.py`、`tests/test_finance.py`、`tests/test_notifications.py`、`tests/test_reports.py`

前端：

- `src/api/finance.js`、`src/api/notifications.js`、`src/api/reports.js`
- `src/utils/format.js`
- `src/views/FinanceView.vue`、`src/views/NotificationsView.vue`、`src/views/ReportsView.vue`
- `src/styles.css`（新增通用统计/表格/表单样式）

未新增数据库迁移：`finance_records`、`notifications`、`audit_logs` 已在初始 Alembic schema 中。

## 8. 验证结果

已在当前环境执行：

| 验证项 | 结果 |
|---|---|
| 后端单元/接口测试（成员 C + 既有 auth/security） | `27 passed` |
| 完整 `pytest` | `27 passed, 1 failed`；唯一失败为 `tests/test_health.py`，原因是没有真实 MySQL |
| OpenAPI schema 生成 | `200`，M05/M06/M07 路由均已注册 |
| 新增后端文件 ruff | `All checks passed` |
| 前端依赖安装 | 完成 |
| 前端构建 | `vite build` 通过，112 modules transformed |

补充验证（2026-10-31，负责人环境）：

- 真实 MySQL 8.4.11 的 Alembic migration、Seed、接口集成验证：已执行并通过；M05 经费登记/汇总、M06 通知发布/收件箱/已读、M07 综合统计/CSV 导出/审计日志均在 `docs/integration/smoke_m01_m07.py` 的 26 项冒烟检查中通过。
- 浏览器端到端点击验证：仍未执行；前端已完成生产构建，接口字段与页面绑定已按契约实现，建议后续按页面补测。

## 9. 验收对照要点

| 编号 | 场景 | 可观察结果 |
|---|---|---|
| AC-FR-17-01 | R02 为本人社团登记一笔支出 | 返回 `ACTIVE` 记录；R03 可查询；其他社团 R02 不可操作 |
| AC-FR-17-02 | R02 作废记录但未填原因 | 返回 `40001`；记录仍为 `ACTIVE` |
| AC-FR-17-03 | R02 作废记录并填写原因 | 记录变为 `VOIDED`，保留原因与原金额；再次作废返回 `40901` |
| AC-FR-18-01 | 按社团、类型、状态和日期过滤 | 列表与汇总只包含权限范围和过滤条件内记录；作废记录不计入收支 |
| AC-FR-19-01 | 用户查看通知并标记已读 | 只能看到本人通知；非本人标记返回 `40301`；未读 → 已读 |
| AC-FR-20-01 | R03 向指定社团发布通知 | 该社团有效成员与负责人收到通知；R01/R02 调用返回 `40301` |
| AC-FR-21-01 | R02 导出本社团经费 CSV | 文件带 UTF-8 BOM，可用 Excel 打开，只含本社团数据；R03 可导出全部或指定社团 |
| AC-FR-22-01 | R04 查询审计日志 | 可看到经费创建/修改/作废和管理通知发布记录；R03/R02/R01 查询返回 `40301` |

## 10. 集成注意事项

1. 当前工作目录不是 git 仓库，未创建 `feature/m05-m06-m07-ops` 分支；请在真实仓库按分支规则提交。
2. `app/core/exceptions.py` 的修改是校验错误序列化的最小修复，需负责人按公共变更规则审查。
3. 前端 R03 的社团过滤使用社团 ID 输入，因为 `GET /clubs` 仍属于成员 A 的 Skeleton；待社团列表接口实现后可替换为下拉选择。
4. 通知接收人包含已停用账号的历史授权/成员关系；账号停用后无法登录，但历史通知保留。若负责人要求停用账号不再接收新通知，可在 `notification_service` 中统一过滤 `User.status`，需先确认需求。
