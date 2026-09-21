# Engineering Baseline V0.1

## 1. 技术栈

- Frontend：Vue 3、Vite、JavaScript、Vue Router、Pinia、Axios。
- Backend：Python 3.11+、FastAPI、SQLAlchemy 2.x、Pydantic 2、Alembic、PyJWT、pytest。
- Database：MySQL 8；Docker Compose 仅提供开发数据库。

没有引入 TypeScript、大型 UI 框架、Redis、消息队列、微服务或 Kubernetes。

## 2. 系统结构

```text
Vue SPA → Axios /api/v1 → FastAPI routers → services/repositories → SQLAlchemy → MySQL 8
                             │
                             ├─ JWT authentication
                             ├─ system role permission (R01/R03/R04)
                             └─ club-scoped R02 permission
```

- Router 层固定 HTTP 契约；Service 层承载状态转换与事务；Repository 层承载查询。
- V0.1 只完整实现 health、login、logout、me。M02～M07 handler 返回统一 501。
- API 成功/失败都经过统一 envelope；HTTP 状态码与业务错误码配合。

## 3. 数据模型摘要

| 模型/表 | 目的 |
|---|---|
| users | 自建/预置测试账号与启停状态 |
| system_role_assignments | R01、R03、R04 系统授权；不存 R02 |
| club_role_assignments | 用户对具体 Club 的 R02 授权 |
| club_registration_applications | R01 发起的社团注册申请 |
| clubs | FR-05 通过后形成的正式社团 |
| annual_review_applications | 年审申请与审核意见 |
| club_members | 学生与社团的成员关系，不是全局角色 |
| membership_applications | 入团/退出申请 |
| activities | 独立保存审核状态和执行状态 |
| activity_registrations | 学生活动报名关系 |
| finance_records | 收入/支出、作废与历史痕迹，不含支付/审核 |
| notifications | 站内通知与未读/已读 |
| audit_logs | 关键操作审计 |
| revoked_tokens | JWT logout 撤销记录 |

共 14 张表。外键默认 RESTRICT，避免账号停用或授权变化删除历史业务数据。

## 4. 权限模型

- R01 是学生基础身份，可发起社团注册、成员申请和活动报名。
- R02 只能由 `club_role_assignments(user_id, club_id, role_code='R02')` 表达。`Principal.club_leader_ids` 和 `require_club_leader` 提供公共校验入口。
- R03 是系统级业务管理员，按既有 FR 访问全部社团业务记录；没有 department/college/scope 字段。
- R04 是系统级技术管理员，负责账号、授权和审计，不参与注册、年审或活动业务审核。
- FR-05 后续实现必须在同一事务中完成申请通过、Club 创建和申请人的社团级 R02 授权。

## 5. Authentication

- 使用本地测试账号与 PBKDF2-SHA256 密码哈希。
- login 签发 HS256 JWT，JWT 包含 `sub`、`username`、`jti`、`iat`、`exp`。
- logout 把 `jti` 写入 `revoked_tokens`；me 汇总系统授权和负责社团。
- 不接入 CAS、OAuth、LDAP、SSO 或学校统一身份认证。

## 6. State management

审核状态 `ReviewStatus` 与活动执行状态 `ActivityExecutionStatus` 是两个字段：

```text
ReviewStatus: DRAFT → PENDING → APPROVED / REJECTED / WITHDRAWN
ActivityExecutionStatus: UNPUBLISHED → REGISTRATION_OPEN → REGISTRATION_CLOSED → IN_PROGRESS → ENDED / CANCELLED
```

数据库只保存合法值；具体可达转换由后续 Service 实现。活动取消与申请撤回不同。年审驳回只保存结果/意见并通知，不触发 Club 或权限冻结。

## 7. API style

- 前缀 `/api/v1`；资源使用复数名词，操作使用显式子路径。
- 成功 code 0；4xx/5xx 业务码见 `docs/api/ERROR_CODES.md`。
- 统一分页 `{items,page,page_size,total}`。
- 详细 endpoint、角色、资源归属、schema 和实现状态见 `docs/api/API_CONTRACT_V0_1.md`。

## 8. Frontend state

- Pinia `auth` store 保存 JWT 和 `/auth/me` 结果。
- Axios interceptor 附加 Bearer token。
- Router guard 保护业务页面；登录后 Dashboard 显示姓名、系统角色和负责社团。
- 其他 View 只显示 M/FR/owner，不实现完整业务 UI。

## 9. Seed 与 Migration

- Alembic revision `20260915_0001` 从空 MySQL 8 数据库创建 14 张表。
- `python -m app.db.seed` 是推荐 Seed；检测到已有用户时跳过，避免重复写入。
- `database/schema.sql` 与 `database/seed.sql` 供审阅/普通 MySQL 方式使用。
- Seed 使用虚构姓名、社团和业务数据；凭据只用于本地。

## 10. Requirements → Engineering mapping

| M / FR | API 分组 | 主要模型 | 后端模块 | Owner |
|---|---|---|---|---|
| M01 / FR-01～FR-02 | `/auth/*`、横切依赖 | users, revoked_tokens, role assignments | auth.py, deps.py, security.py, permissions.py | Leader |
| M01 / FR-23 | `/accounts/*` | users, system_role_assignments, club_role_assignments, audit_logs | accounts.py | Leader |
| M02 / FR-03～FR-05 | `/club-registration-applications*`, `/clubs*` | club_registration_applications, clubs, club_role_assignments | clubs.py | Member A |
| M02 / FR-06～FR-07 | `/annual-reviews*` | annual_review_applications, notifications | annual_reviews.py | Member A |
| M03 / FR-08～FR-10 | `/membership-applications*`, `/clubs/{id}/members*` | membership_applications, club_members | members.py | Member A |
| M04 / FR-11～FR-16 | `/activities*` | activities, activity_registrations, notifications | activities.py | Member B |
| M05 / FR-17～FR-18 | `/finance-records*` | finance_records | finance.py | Member C |
| M06 / FR-19～FR-20 | `/notifications*` | notifications | notifications.py | Member C |
| M07 / FR-21～FR-22 | `/reports*`, `/audit-logs` | aggregate queries, audit_logs | reports.py | Member C |

## 11. 开发协作约定

1. 先运行 migration 和 Seed，再开发模块。
2. 业务实现必须引用 FR 编号并遵守 API Contract。
3. 状态变化放在 Service 事务，不放数据库 Trigger。
4. 新迁移只增量创建，不修改已共享 migration 历史。
5. 公共接口改变需通知所有 owner；需求改变必须走 CR。
6. V0.1 不实现范围外功能，也不替成员完成 M02～M07。
