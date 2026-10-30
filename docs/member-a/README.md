# 成员 A 交付物：M02 / M03 / M07-A

> 本目录是成员 A 的实现、测试与文档，**已提交到分支 `feature/m02-m03-club-member`；`main` 未直接修改**。
> 代码合并位置见 [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md)，该指南同时保留作为复盘记录。

## 1. 任务范围

依据仓库中的以下文件确定范围：

- `docs/team/README.md`：成员 A 阅读 M02、M03 契约与 FR-03～FR-10。
- `docs/development/MODULE_OWNERSHIP.md`：成员 A 负责 M02、M03。
- `README.md` 的 TODO：`M02/M03 Service、Repository、领域 Schema、测试和 UI`。
- `ENGINEERING_SKELETON_V0_1_FINAL.md`：成员 A 负责 M02、M03、M07-A（社团/成员统计）。
- `REQUIREMENTS_BASELINE_V1_1.md`：FR-03～FR-10，以及 FR-21 中社团/成员部分。
- `docs/api/API_CONTRACT_V0_1.md`：M02、M03 的路径、method、FR 映射和错误码。

本次交付：

| 模块 | 功能 | 交付 |
|---|---|---|
| M02 | 社团注册申请、注册审核、社团资料、年审 | 后端 API + Service + Repository + Schema + 通知/审计写入 + 前端页面 |
| M03 | 入团/退出申请、申请处理、成员名册、社团职务 | 后端 API + Service + Repository + Schema + 通知/审计写入 + 前端页面 |
| M07-A | 社团/成员统计 | 查询 Service + Schema + 测试 + 集成说明（按契约不新增公共 URL） |

## 2. 目录结构

```text
成员A/
├─ backend/
│  ├─ app/
│  │  ├─ api/v1/clubs.py               # 替换 Skeleton
│  │  ├─ api/v1/annual_reviews.py      # 替换 Skeleton
│  │  ├─ api/v1/members.py             # 替换 Skeleton
│  │  ├─ schemas/club.py               # 新增
│  │  ├─ schemas/member.py             # 新增
│  │  ├─ schemas/statistics.py         # 新增
│  │  ├─ repositories/club_repository.py
│  │  ├─ repositories/member_repository.py
│  │  ├─ services/club_service.py
│  │  ├─ services/member_service.py
│  │  ├─ services/club_member_events.py
│  │  └─ services/club_member_statistics.py
│  └─ tests/                           # 新增 41 个测试
├─ frontend/
│  └─ src/
│     ├─ api/clubs.js                  # 新增
│     ├─ api/members.js                # 新增
│     ├─ utils/m02m03.js               # 新增
│     ├─ views/ClubsView.vue           # 替换占位页
│     └─ views/MembersView.vue         # 替换占位页
├─ docs/                               # 实现、API、测试、集成、验收、截图与工程问题
└─ integration/
   ├─ reports_m07a_snippet.py          # 供 M07 owner 组合 /reports/summary 的示例
   ├─ smoke_m02_m03.py                 # 需要 MySQL 的端到端联调脚本
   └─ browser_acceptance.js            # Chrome + Playwright 浏览器验收脚本
```

## 3. 关键设计结论

1. **R02 不是全局角色**：所有社团权限都检查 `ClubRoleAssignment` 的用户—具体 `club_id` 关系。
2. **注册通过 = 一个事务**：建立 `Club`、写入申请人该社团的 `R02`、写入负责人成员关系、写通知/审计；驳回不建立社团、不授权。
3. **年审驳回不冻结**：只写年审状态、意见和站内通知，不修改社团、账号或其他业务权限。
4. **申请状态与活动执行状态无关**：本交付不实现 M04 的活动状态机。
5. **M07-A 不新增 URL**：API Contract 只定义 `/reports/summary`；提供 `club_member_statistics()` 查询服务，由 M07 owner 组合。
6. **通知/审计是业务事务的一部分**：写 `notifications`、`audit_logs` 表，但不修改 M06/M07 的查询路由。
7. **无数据库结构变更**：复用现有 14 张业务表和 Alembic 初始迁移，不新增 migration。

## 4. 已验证内容

在本机 Windows 环境使用隔离 venv 执行：

```text
pytest -q                       45 passed
ruff check <成员A文件>          All checks passed
npm.cmd run build               110 modules transformed, built successfully
MySQL 8.4.11 migration + seed   PASS
smoke_m02_m03.py                ALL PASS
Chrome 156 + Playwright         9 步浏览器流程 PASS，9 张截图
```

说明：

- **真实 MySQL 联调已完成**：migration、seed、health、登录、注册→审核→R02、年审、入团、名册、M07-A 统计和错误路径均通过。详见 [`docs/REAL_DB_AND_BROWSER_ACCEPTANCE.md`](docs/REAL_DB_AND_BROWSER_ACCEPTANCE.md)。
- **浏览器验收已完成**：使用系统 Chrome + Playwright Core 跑通主流程，并验证 R03 名册 403；截图在 [`docs/screenshots/`](docs/screenshots/)。
- **Docker 偏差**：本机当前用户不是管理员且未安装 WSL2，Docker Desktop 无法安装；真实数据库验证使用了便携版 MySQL 8.4.11（与 `mysql:8.4` 同属 8.4），Docker 容器本身未验证。
- 单元/契约测试仍不连接 MySQL、不使用 SQLite；真实 SQL 由上述联调单独覆盖。

## 5. 阅读顺序

1. [`docs/M02_M03_IMPLEMENTATION.md`](docs/M02_M03_IMPLEMENTATION.md)：业务规则、权限、状态机、事务与副作用。
2. [`docs/API_M02_M03.md`](docs/API_M02_M03.md)：请求/响应字段与错误码。
3. [`docs/M07A_CLUB_MEMBER_STATISTICS.md`](docs/M07A_CLUB_MEMBER_STATISTICS.md)：统计服务及与 M07 的集成。
4. [`docs/INTEGRATION_GUIDE.md`](docs/INTEGRATION_GUIDE.md)：逐文件合并与联调命令。
5. [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md)：测试清单、命令与结果。
6. [`docs/REAL_DB_AND_BROWSER_ACCEPTANCE.md`](docs/REAL_DB_AND_BROWSER_ACCEPTANCE.md)：真实 MySQL 与浏览器验收证据。
7. [`docs/ENGINEERING_NOTES.md`](docs/ENGINEERING_NOTES.md)：需要负责人确认的工程问题（不擅自改需求）。
8. [`docs/ACCEPTANCE_CHECKLIST.md`](docs/ACCEPTANCE_CHECKLIST.md)：FR-03～FR-10 验收对照。

## 6. 明确未做的内容

- 未修改需求基线、角色、模块、FR 编号、状态名称或系统边界。
- 未实现活动、经费、通知中心、审计查询、账号授权等其他人负责的模块。
- 未实现签到、支付、报销、外部通知、多级审批、SSO 等范围外能力。
- 未在 Docker Desktop / 容器中运行 MySQL；本机无管理员权限和 WSL2，改用同版本便携 MySQL 8.4.11 完成真实联调。
- 已提交到 `feature/m02-m03-club-member` 分支；`main` 未直接修改；验证环境未提交。
