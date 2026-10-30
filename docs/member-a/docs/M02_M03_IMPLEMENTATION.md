# M02 / M03 实现说明

> 适用基线：`REQUIREMENTS_BASELINE_V1_1.md`、`docs/api/API_CONTRACT_V0_1.md`、`ENGINEERING_SKELETON_V0_1_FINAL.md`。
> 本文只描述成员 A 的实现，不修改需求、不新增角色/模块/FR/状态。

## 1. 分层与职责

| 层 | 文件 | 职责 |
|---|---|---|
| API | `app/api/v1/clubs.py` | 注册申请、社团资料；保持路径/method/response envelope |
| API | `app/api/v1/annual_reviews.py` | 年审；前缀 `/annual-reviews` |
| API | `app/api/v1/members.py` | 成员申请、处理、名册、职务 |
| Schema | `app/schemas/club.py`、`member.py`、`statistics.py` | 领域请求/响应字段与校验 |
| Service | `app/services/club_service.py` | 权限、状态机、事务、唯一性、通知/审计编排 |
| Service | `app/services/member_service.py` | 入团/退出、成员关系同步、名册范围 |
| Service | `app/services/club_member_events.py` | 站内通知和审计写入（只写表，不提供查询 API） |
| Service | `app/services/club_member_statistics.py` | M07-A 统计查询，不注册新 URL |
| Repository | `app/repositories/club_repository.py`、`member_repository.py` | SQL 查询与持久化，不含权限/状态判断 |

Service 返回可被 Pydantic 校验的 `dict`，Router 统一包装为：

```json
{"code": 0, "message": "success", "data": ...}
```

错误使用现有 `AppError` 和 `docs/api/ERROR_CODES.md`，不新增错误码。

## 2. 权限矩阵（本次实现的实际判断）

| 操作 | R01 | R02（目标社团） | R02（其他社团） | R03 | R04 |
|---|---|---|---|---|---|
| 创建社团注册申请 | 允许（本人） | 允许（本人，同时具备 R01） | 同左 | 允许（本人，同时具备 R01） | 无 R01 时拒绝 |
| 查看注册申请列表 | 仅本人 | 仅本人 | 仅本人 | 全部 | 仅本人 |
| 编辑/提交/撤回注册申请 | 仅本人且草稿/已撤回；撤回仅待审核 | 同左 | 同左 | 同左 | 同左 |
| 审核注册申请 | 拒绝 | 拒绝 | 拒绝 | 允许；不得审核本人申请 | 拒绝 |
| 查看社团列表/详情 | 允许 | 允许 | 允许 | 允许 | 允许 |
| 修改社团资料 | 拒绝 | 允许 | 拒绝 | 拒绝（只查看） | 拒绝 |
| 创建/编辑/提交/撤回年审 | 拒绝 | 允许 | 拒绝 | 拒绝 | 拒绝 |
| 查看年审列表 | 拒绝 | 本社团 | 拒绝 | 全部 | 拒绝 |
| 审核年审 | 拒绝 | 拒绝 | 拒绝 | 允许；不得审核本人提交 | 拒绝 |
| 提交入团/退出申请 | 允许（本人） | 允许（本人，同时具备 R01） | 同左 | 允许（本人，同时具备 R01） | 无 R01 时拒绝 |
| 查看成员申请 | 仅本人 | 本人申请 + 负责社团申请 | 仅本人 | 仅本人（契约未授予 R03 全量） | 仅本人 |
| 撤回成员申请 | 仅本人且待处理 | 同左 | 同左 | 同左 | 同左 |
| 处理成员申请 | 拒绝 | 允许；不得处理本人申请 | 拒绝 | 拒绝 | 拒绝 |
| 查看成员名册 | 本社团有效成员：仅本人记录、受限字段 | 负责社团：完整名册 | 拒绝 | 非负责人/非成员时拒绝 | 拒绝 |
| 维护社团职务 | 拒绝 | 允许（仅有效成员） | 拒绝 | 拒绝 | 拒绝 |
| M07-A 社团/成员统计 | 拒绝 | 负责社团 | 拒绝 | 全部 | 拒绝 |

说明：

- “同时具备 R01”是数据事实：本系统 R02/R03/R04 是附加授权，不是替代 R01 的全局角色。Service 对 R01 发起类操作显式检查 `R01`。
- 申请人与审核/处理人为同一人时，注册审核、年审审核、成员处理均拒绝（业务基线要求）。
- R03 对成员申请/名册的范围：API Contract 第 6 节只写“R01 本人或目标社团 R02”，因此实现按契约拒绝 R03 全量访问；如负责人认为 CR-04 应覆盖 M03，请按 `docs/ENGINEERING_NOTES.md` 的 EI-A-03 决策后再改。

## 3. 状态机

### 3.1 社团注册申请 / 年审申请（`ReviewStatus`）

```text
DRAFT ──submit──> PENDING ──review APPROVED──> APPROVED
  ↑                  │
  │                  ├──review REJECTED──> REJECTED
  │                  └──withdraw──> WITHDRAWN
  └──────edit──── WITHDRAWN ──submit──> PENDING
```

- 只有 `DRAFT` / `WITHDRAWN` 可编辑、可提交。
- 只有 `PENDING` 可撤回、可审核。
- `APPROVED` / `REJECTED` 不可回退；本交付不实现“复制/修订形成新轮次”的复用规则（见 EI-A-02）。
- 驳回注册申请不建立 Club、不写 `ClubRoleAssignment`；驳回年审不修改 Club、账号或其他业务。

### 3.2 入团/退出申请（`MembershipApplicationStatus`）

```text
PENDING ──process APPROVED──> APPROVED
   │
   ├──process REJECTED──> REJECTED
   └──withdraw──────────> WITHDRAWN
```

成员关系同步：

| 申请类型 | 处理结果 | 成员关系变化 |
|---|---|---|
| JOIN | APPROVED | 无记录则新建 `ACTIVE`；原 `EXITED` 则恢复 `ACTIVE`，清空旧职务，刷新 `joined_at`，清空 `exited_at` |
| JOIN | REJECTED | 不变 |
| EXIT | APPROVED | 原 `ACTIVE` → `EXITED`，写 `exited_at`；保留历史 `position_name` |
| EXIT | REJECTED | 不变 |

同一用户对同一社团同时只能存在一条 `PENDING` 成员申请；已是 `ACTIVE` 成员不能再申请入团；非 `ACTIVE` 成员不能申请退出。

## 4. 关键业务规则

### FR-03 社团注册申请

1. 任何具备 R01 的登录用户都可以以自己的身份创建申请，客户端不能指定 `applicant_user_id`。
2. 新建固定为 `DRAFT`，`submitted_at` 为空。
3. 编辑只能改 `proposed_name`、`description`、`advisor_contact`；不能改状态、申请人、审核人。
4. 提交写入 `submitted_at`，清空上一次审核痕迹，并通知所有有效 R03。
5. 撤回只允许 `PENDING`，写入 `WITHDRAWN`。
6. 列表分页 `page` 从 1 开始、`page_size` 1～100；R03 看全部，其他用户只看本人。
7. 可选 `status` 过滤，不改变路径语义。

### FR-04 社团资料

1. 登录用户可查询社团列表和详情；当前模型没有“未发布社团”，因此返回所有已建立的 Club。
2. 只有目标社团的有效 R02 可以修改 `name`、`description`、`advisor_contact`。
3. 社团名称保持全局唯一；冲突返回 `40902`。
4. R03 只查看，不代替负责人修改业务材料。

### FR-05 社团注册审核

1. 仅 R03；`PENDING` → `APPROVED` / `REJECTED`。
2. 驳回必须填写非空理由，写 `review_comment`、`reviewed_by`、`reviewed_at`。
3. 通过时在**同一事务**内：
   - 校验申请仍为 `PENDING`、申请人不是审核人、名称未被占用；
   - 建立 `Club`（`registration_application_id` 唯一）；
   - 建立申请人针对该 Club 的 `ClubRoleAssignment(role_code="R02", active=True)`；
   - 建立申请人的 `ClubMember(status=ACTIVE, position_name="负责人")`；
   - 写申请人站内通知；
   - 写审计日志。
4. 驳回时不建立 Club、不建立 `ClubRoleAssignment`，只写申请状态/意见/通知/审计。
5. 并发审核使用 `SELECT ... FOR UPDATE` 锁申请行；Club 的唯一约束作为最后防线，冲突返回 `40902`。

### FR-06 / FR-07 年审

1. 创建必须指定 `club_id`、`review_year`、`materials`；调用者必须是该社团 R02。
2. 同一 `(club_id, review_year)` 只能有一条记录（数据库唯一约束）；重复返回 `40902`。
3. 草稿/已撤回可编辑；提交后 `submitted_by` 记为实际提交人。
4. R03 审核；驳回必须填写意见；审核人不得是提交人。
5. 审核只写年审记录、意见和通知；**不冻结社团、不停用账号、不禁止活动/成员/经费业务**。
6. 列表：R03 全部；R02 只看自己负责社团；R01/R04 无权限（`40301`）。

### FR-08 入团与退出申请

1. 申请人是当前登录用户；客户端不能伪造。
2. JOIN：社团必须存在；不能已是 `ACTIVE` 成员；不能已有 `PENDING` 申请。
3. EXIT：必须是 `ACTIVE` 成员；不能已有 `PENDING` 申请。
4. 新建为 `PENDING`，通知该社团所有有效 R02。
5. 撤回仅本人且 `PENDING`。

### FR-09 成员申请处理

1. 仅目标社团有效 R02；`PENDING` → `APPROVED` / `REJECTED`。
2. 申请人不得处理自己的申请。
3. 同意 JOIN / EXIT 时同步成员关系（见 3.2）；驳回不改成员关系。
4. 写 `processed_by`、`processed_at`、`process_comment`，通知申请人，写审计。
5. 使用行锁 + 唯一约束处理并发；冲突返回 `40901/40902`。

### FR-10 成员名册与职务

1. 负责人（目标社团 R02）可查看完整名册：账号、姓名、职务、状态、加入/退出时间。
2. 本社团有效成员只能查看**本人**的有效记录，且只返回 `id/club_id/display_name/position_name/status`，不返回 `user_id/username/joined_at/exited_at`。
3. 非负责人且非有效成员返回 `40302`。
4. 维护职务仅负责人、仅 `ACTIVE` 成员；可设置或清空 `position_name`（最长 100）。
5. 职务变更写审计；成员退出时保留历史职务，重新入团时清空旧职务。

## 5. 通知与审计

### 5.1 通知事件

写入现有 `notifications` 表，`read_status=UNREAD`，由 M06 的查询/已读接口消费。

| event_type | 触发 | 收件人 |
|---|---|---|
| `CLUB_REGISTRATION_SUBMITTED` | 注册申请提交 | 所有有效 R03 |
| `CLUB_REGISTRATION_APPROVED` | 注册审核通过 | 申请人 |
| `CLUB_REGISTRATION_REJECTED` | 注册审核驳回 | 申请人 |
| `ANNUAL_REVIEW_SUBMITTED` | 年审提交 | 所有有效 R03 |
| `ANNUAL_REVIEW_APPROVED` / `ANNUAL_REVIEW_REJECTED` | 年审审核 | 提交人 |
| `MEMBERSHIP_APPLICATION_SUBMITTED` | 成员申请提交 | 目标社团所有有效 R02 |
| `MEMBERSHIP_APPLICATION_APPROVED` / `MEMBERSHIP_APPLICATION_REJECTED` | 成员申请处理 | 申请人 |

### 5.2 审计事件

写入现有 `audit_logs` 表，`resource_id` 使用业务主键字符串：

| action | 资源 |
|---|---|
| `CLUB_REGISTRATION_CREATE` / `UPDATE` / `SUBMIT` / `WITHDRAW` / `REVIEW` | `club_registration_application` |
| `CLUB_PROFILE_UPDATE` | `club` |
| `ANNUAL_REVIEW_CREATE` / `UPDATE` / `SUBMIT` / `WITHDRAW` / `REVIEW` | `annual_review_application` |
| `MEMBERSHIP_JOIN_APPLY` / `MEMBERSHIP_EXIT_APPLY` / `MEMBERSHIP_APPLICATION_WITHDRAW` / `MEMBERSHIP_APPLICATION_PROCESS` | `membership_application` |
| `CLUB_MEMBER_POSITION_UPDATE` | `club_member` |

`ip_address` 当前为 `NULL`：Service 没有直接读取 `Request`，避免把 HTTP 细节下沉到业务层；如后续需要，可在 Router 注入后传给 Service。

## 6. 事务边界与并发

| 操作 | 事务内容 |
|---|---|
| 注册申请创建/编辑/提交/撤回 | 申请行 + 审计 +（提交时）通知 |
| 注册审核 | 申请行锁 + 状态 +（通过时）Club/R02/负责人成员 + 通知 + 审计 |
| 社团资料修改 | Club 行锁 + 字段 + 审计 |
| 年审创建/编辑/提交/撤回 | 年审行 + 审计 +（提交时）通知 |
| 年审审核 | 年审行锁 + 状态/意见 + 通知 + 审计 |
| 成员申请创建 | 成员申请 + 通知 + 审计 |
| 成员申请处理 | 成员申请行锁 + 成员关系行锁 + 同步 + 通知 + 审计 |
| 职务维护 | 成员行锁 + 字段 + 审计 |

并发要点：

- `SELECT ... FOR UPDATE` 用于审核/处理类操作，避免重复通过。
- 数据库唯一约束（`clubs.registration_application_id`、`clubs.name`、`uq_club_review_year`、`uq_club_member`）是最终一致性保障。
- 捕获 `IntegrityError` 时回滚并返回 `40902`（重复/唯一性冲突），不返回 500。
- `db.commit()` 只在 Service 内调用一次；失败回滚，不把半成品返回给 API。

## 7. 与公共层的关系

本交付**没有修改**：

- `app/db/models/domain.py`、`database/schema.sql`、`alembic/versions/*`
- `app/api/deps.py`、`app/core/permissions.py`、`app/core/exceptions.py`
- `app/schemas/common.py`、`app/schemas/business.py`
- `app/api/v1/__init__.py`、`app/main.py`
- 前端 `router/index.js`、`components/AppLayout.vue`、`api/client.js`、`stores/auth.js`

新增的 Service 只调用现有 `Principal`、`require_system_role`、`require_club_leader` 和 ORM 模型；没有新增全局角色、公共响应结构或错误码。

## 8. 已识别的工程边界

详见 [`ENGINEERING_NOTES.md`](ENGINEERING_NOTES.md)：

- EI-A-01：M07-A 没有独立 API 契约，按契约只提供统计 Service。
- EI-A-02：年审 `(club_id, review_year)` 唯一约束与“驳回后重新提交”规则未在基线细化。
- EI-A-03：R03 是否应全量访问 M03 申请/名册，API Contract 与 CR-04 的表述需要负责人确认。
- EI-A-04：M02/M03 直接写 `notifications` / `audit_logs`，需要 M06/M07 owner 知悉消费方式。
