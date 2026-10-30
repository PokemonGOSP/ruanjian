# Engineering Validation V0.1

> 验证日期：2026-09-21（初版），2026-10-31（全模块集成复验）

## 1. 环境与数据库

| 验证项 | 状态 | 实际结果 |
|---|---|---|
| Python | PASS | WSL Python 3.12.3；临时 venv 可用 |
| Node/npm | PASS | Node 24.16.0，npm 11.13.0 |
| Docker | PASS | Docker 29.8.0，Compose 5.5.1 |
| MySQL 8 | PASS | `mysql:8.4`，Server 8.4.11，容器 healthy，3306 映射可用 |
| DB connectivity | PASS | Backend 通过 PyMySQL 连接 `club_management` |
| Alembic migration | PASS | 真实执行 `alembic upgrade head`，版本 `20260915_0001` |
| 实际表数量 | PASS | 15 张物理表：14 张业务表 + `alembic_version` |
| Seed | PASS | 首次写入 6 users、3 clubs、申请/活动/经费/通知数据；第二次安全跳过 |

## 2. Backend 与认证

| 验证项 | 状态 | 实际结果 |
|---|---|---|
| Backend start | PASS | Uvicorn 监听 8000 |
| Health | PASS | `GET /api/v1/health` 返回 `service=up,database=up` |
| Login | PASS | `leader01 / Leader123!` 返回真实 JWT |
| Invalid login | PASS | 错误密码和不存在账号均返回 HTTP 401 |
| Disabled login | PASS | 临时将 `student02` 设为 DISABLED 后返回 HTTP 401，随后恢复 NORMAL |
| `/auth/me` | PASS | 真实 JWT 返回 user id、username、display name、system roles、club authorizations |
| No/invalid token | PASS | 无 token 与非法 token 均返回 HTTP 401 |
| R02 resource authorization | PASS | `leader01` 的 R02 仅关联具体 Club 1、Club 3；system role 仍为 R01，不存在全局 `users.role=R02` |
| pytest | PASS | `4 passed, 2 warnings`（单元/依赖覆盖测试） |
| MySQL integration validation | PASS | 真实 migration、Seed、health、login、disabled login、`/auth/me` 已完成 |

## 3. Frontend

| 验证项 | 状态 | 实际结果 |
|---|---|---|
| Axios base URL | PASS | 默认 `http://127.0.0.1:8000/api/v1`，支持 `VITE_API_BASE_URL` |
| CORS | PASS | 后端允许 localhost/127.0.0.1:5173 |
| Login/token storage | PASS | LoginView 调用真实 `/auth/login`，Pinia 使用 localStorage 保存 token |
| `/auth/me`/Dashboard | PASS | auth store 获取真实用户，路由进入 Dashboard 显示当前身份 |
| Frontend install | PASS | `npm.cmd install`，0 vulnerabilities |
| Frontend build | PASS | Vite 7.3.6，105 modules transformed |
| Frontend ↔ Backend auth chain | PASS | 配置、API client、token storage、`/auth/me` 与 Dashboard 链路一致 |

## 4. Skeleton 一致性

| 验证项 | 状态 | 实际结果 |
|---|---|---|
| API operations | PASS | 56 |
| 已实现 operations | PASS | 4：health、login、logout、me |
| Skeleton operations | PASS | 52，仍保留 Skeleton / HTTP 501 |
| API Contract | PASS | FR-01～FR-23 覆盖完整，无缺失或额外项 |
| SQLite/替代数据库 | PASS | 未使用 SQLite、PostgreSQL、MariaDB 或其他替代数据库 |

## 5. 全模块集成验证（2026-10-31）

真实 MySQL 8.4（Server 8.4.11，`club_management`）上执行 migration（`20260915_0001`）与 Seed 后，对 M01～M07 做端到端联调。

| 验证项 | 状态 | 实际结果 |
|---|---|---|
| Backend pytest | PASS | 95 passed |
| M01 FR-23 账号管理 | PASS | 账号列表、非 R04 返回 403、创建（自动 R01）、停用/恢复、授予/撤销 R03、授予/撤销社团 R02、R02 缺少 club_id 返回 400 |
| M02/M03 社团与成员 | PASS | 成员 A 的 `smoke_m02_m03.py` 全部通过 |
| M04 活动管理 | PASS | 草稿 → 提交 → R03 审核通过 → 发布 → 学生报名 → 取消报名 |
| M05 经费 | PASS | 登记支出、按社团汇总 |
| M06 通知 | PASS | 管理通知发布、学生收件箱、标记已读 |
| M07 统计与审计 | PASS | 综合统计（社团/成员/活动/报名）、经费 CSV 导出、审计日志查询 |
| Frontend build | PASS | Vite 构建成功，120 modules transformed |

## 6. 最终状态

- `REQUIRES_CR`：不存在。
- EI-01～EI-05 已全部解除，详见 `ENGINEERING_ISSUES_V0_1.md`。
- 工程状态：`ALL_MODULES_IMPLEMENTED_AND_INTEGRATION_VERIFIED`。
