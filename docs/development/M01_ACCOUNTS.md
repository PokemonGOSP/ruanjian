# M01 账号与角色授权（FR-23）

> Owner：Leader / Integration
> 需求：`REQUIREMENTS_BASELINE_V1_1.md` FR-02、FR-23
> 契约：`docs/api/API_CONTRACT_V0_1.md` 账号相关 6 个 operation

## 1. 范围

R04 系统管理员维护本地测试账号，并按项目授权规则授予/撤销 R02、R03、R04 授权身份。

- 不实现注册、SSO、密码找回、批量导入或删除账号。
- 账号与授权变更只做状态停用，不删除历史业务数据。
- R01 是创建账号时自动授予的基础身份，不可撤销。
- R02 必须绑定具体社团，使用 `club_role_assignments`；不得写成全局 `users.role`。
- R03、R04 为系统级授权，不能携带 `club_id`。
- 所有创建、更新、授予、撤销动作写入 `audit_logs`，供 M07 审计查询。

## 2. 后端

| 层 | 文件 |
|---|---|
| API | `backend/app/api/v1/accounts.py` |
| Schema | `backend/app/schemas/business.py`（`AccountCreateRequest`、`AccountUpdateRequest`、`RoleAssignmentRequest` 等） |
| 模型 | `backend/app/db/models/domain.py`（`User`、`SystemRoleAssignment`、`ClubRoleAssignment`、`AuditLog`） |
| 测试 | `backend/tests/test_accounts.py`（15 个用例） |

| Method | Path | 说明 | 错误码 |
|---|---|---|---|
| GET | `/accounts` | R04 分页列出账号，不返回凭据字段 | 40101、40301 |
| POST | `/accounts` | 创建本地账号并授予 R01 | 40001、40301、40902 |
| PATCH | `/accounts/{id}` | 修改显示名称或启停状态 | 40301、40401、40901 |
| POST | `/accounts/{id}/role-assignments` | 授予 R02（带 `club_id`）/R03/R04 | 40002、40301、40401、40902 |
| DELETE | `/accounts/{id}/role-assignments/{role_code}` | 撤销 R03/R04，仅置 `active=false` | 40301、40401、40901 |
| DELETE | `/accounts/{id}/club-role-assignments/{club_id}` | 撤销某社团 R02，仅置 `active=false` | 40301、40401、40901 |

## 3. 前端

`frontend/src/views/AccountsView.vue` + `frontend/src/api/accounts.js`：

- 仅 `system_roles` 含 R04 时展示管理界面，其余身份显示无权限提示。
- 账号表：状态、系统角色、社团 R02 授权；支持分页。
- 新建账号（用户名、显示名称、初始密码）。
- 编辑账号显示名称与启停状态。
- 授予角色：选择账号与角色；选择 R02 时联动加载社团下拉。
- 撤销 R03/R04 与社团 R02，操作前二次确认。

## 4. 验证

| 验证项 | 结果 |
|---|---|
| `pytest tests/test_accounts.py` | 15 passed（正向/权限/冲突/404） |
| 集成后全量 `pytest` | 99 passed（含契约一致性测试与异常响应测试） |
| `ruff check app/api/v1/accounts.py` | 通过 |
| 前端 `npm run build` | 通过（120 modules） |
| 真实 MySQL 端到端 | 通过：账号列表、403、创建、停用/恢复、R03/R02 授予撤销、R02 缺 `club_id` 共 12 项冒烟检查，见 `docs/integration/smoke_m01_m07.py`（2026-10-31） |

## 5. 已知限制

- 没有前端自动化测试，页面以构建通过和后端契约测试保障。
- 真实数据库联调（migration + seed + 浏览器操作）待 EI-04 解除后补做。
