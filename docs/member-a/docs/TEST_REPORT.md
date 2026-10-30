# 成员 A 测试报告

> 验证日期：2026-10-30
> 验证环境：Windows，Python 3.12.6，MySQL 8.4.11（便携实例，端口 3307），Node 22.12.0，Chrome 156.0.8078.48
> 验证方式：把 `成员A/` 文件合并到 `ruanjian-main` 的**临时验证副本**后执行；真实数据库和浏览器验收记录见 [`REAL_DB_AND_BROWSER_ACCEPTANCE.md`](REAL_DB_AND_BROWSER_ACCEPTANCE.md)。

## 1. 结果摘要

| 项目 | 结果 | 说明 |
|---|---|---|
| 后端 pytest | **45 passed** | 原仓库 4 个测试 + 成员 A 41 个测试 |
| 后端 Ruff | **All checks passed** | 仅检查成员 A 新增/替换的 Python 文件 |
| OpenAPI 契约 | **47 paths / 56 operations** | M02/M03 端点全部注册，未新增公共 URL |
| 前端 Vite build | **成功** | `110 modules transformed`，产出 `dist/` |
| 真实 MySQL 联调 | **PASS** | MySQL 8.4.11，migration/seed/health/登录/注册→审核→R02/年审/入团/名册全部通过 |
| 浏览器 E2E | **PASS** | Chrome 156 + Playwright Core，9 张截图，无 JS 页面错误、无 5xx |

## 2. 后端测试

### 2.1 命令

```powershell
cd D:\软件\ruanjian-main\backend
.\.venv\Scripts\python.exe -m pytest -q
```

### 2.2 实际输出

```text
............................................                             [100%]
45 passed, 1 warning
```

警告来自 FastAPI/Starlette 的 `TestClient` 弃用提示，不是本交付代码的失败。

### 2.3 用例分布

| 文件 | 数量 | 覆盖重点 |
|---|---:|---|
| `tests/test_auth.py` | 2 | 原仓库登录/JWT/`/auth/me` |
| `tests/test_health.py` | 1 | 原仓库健康检查 |
| `tests/test_security.py` | 1 | 原仓库密码哈希一致性 |
| `tests/test_m02_clubs.py` | 11 | 注册创建/编辑/提交/撤回/审核、R02 授权、权限、路由契约 |
| `tests/test_m02_annual_reviews.py` | 9 | 年审创建/提交/撤回/审核、驳回意见、不冻结社团、范围 |
| `tests/test_m02_m03_api_contract.py` | 5 | 真实 FastAPI 路由、Pydantic 响应序列化、分页校验 |
| `tests/test_m03_members.py` | 12 | 入团/退出规则、重复申请、处理同步成员关系、名册范围、职务 |
| `tests/test_m07a_statistics.py` | 4 | R02/R03 范围、R01 拒绝、统计口径 |

### 2.4 测试方法

- **不使用 SQLite**，也不把 `DATABASE_URL` 改成替代数据库。
- `FakeDb` 只记录 `add/commit/rollback`、通知查询返回值和对象 ID；Repository 函数由 `monkeypatch` 替换，用于验证 Service 的权限、状态转换、事务内副作用。
- `tests/test_m02_m03_api_contract.py` 使用 `TestClient` 和依赖覆盖，验证 Router 的请求校验、`ApiResponse`/`PageData` 序列化和错误码映射。
- 单元/契约测试不连接 MySQL；真实 SQL 部分由第 4 节的 MySQL 联调补充验证覆盖。

### 2.5 关键断言示例

- 注册审核通过：同一事务出现 `Club`、`ClubRoleAssignment(role_code="R02")`、`ClubMember(ACTIVE)`、申请人通知、审计。
- 注册审核驳回：不出现 `Club`/`ClubRoleAssignment`，只写状态、意见、通知、审计。
- 年审驳回：年审状态 `REJECTED`、意见保存、通知提交人；测试断言没有新增/修改 `Club`。
- 成员处理：同意 JOIN 建立 `ClubMember(ACTIVE)`；同意 EXIT 置 `EXITED` 并写 `exited_at`；驳回不建立成员关系。
- 名册：负责人得到完整名册；有效成员只得到本人的受限字段（`user_id=null`、`joined_at=null`）；非成员 `40302`。
- R02 越权：审核/处理其他社团返回 `40302`；R01 审核返回 `40301`；申请人与审核人相同返回 `40301`。

## 3. 后端静态检查

```powershell
cd D:\软件\ruanjian-main\backend
.\.venv\Scripts\python.exe -m ruff check `
  app/api/v1/clubs.py app/api/v1/annual_reviews.py app/api/v1/members.py `
  app/schemas/club.py app/schemas/member.py app/schemas/statistics.py `
  app/repositories/club_repository.py app/repositories/member_repository.py `
  app/services/club_service.py app/services/member_service.py `
  app/services/club_member_events.py app/services/club_member_statistics.py `
  tests/conftest.py tests/helpers.py tests/test_m02_clubs.py `
  tests/test_m02_annual_reviews.py tests/test_m03_members.py `
  tests/test_m07a_statistics.py tests/test_m02_m03_api_contract.py
```

实际输出：

```text
All checks passed!
```

> 说明：仓库原有的 `app/db/models/domain.py`、`app/db/seed.py`、`app/api/v1/__init__.py` 等文件存在既有的行宽/导入排序告警，成员 A 未修改这些公共文件，也不在本报告的“通过”范围内。

## 4. 真实 MySQL 联调（已执行）

### 4.1 环境偏差说明

计划使用 Docker Desktop + `mysql:8.4` 容器，但本机：

- 当前用户不是管理员（Medium integrity）；
- 未安装 WSL2；
- 未安装 Docker。

因此 **Docker Desktop 无法在本机安装**，本轮改用 **便携版 MySQL 8.4.11**（与 `docker-compose.yml` 的 `mysql:8.4` 同属 8.4，服务端版本 8.4.11）完成真实数据库联调。数据库实例位于 `D:\mysql84`，监听 `127.0.0.1:3307`，不属于仓库文件。

### 4.2 执行结果

```text
MySQL 8.4.11                    PASS
CREATE DATABASE / club_app      PASS
alembic upgrade head            PASS（15 张物理表：14 业务表 + alembic_version）
python -m app.db.seed           PASS（6 users、3 clubs、申请/活动/经费/通知）
GET /api/v1/health              PASS（service=up, database=up）
smoke_m02_m03.py                PASS
```

`smoke_m02_m03.py` 实际输出：

```text
[1] 四个测试账号登录成功
[2] student02 创建注册申请 #7，状态 DRAFT
[3] 注册申请已提交，状态 PENDING
[4] manager01 能在待审核列表中看到申请，共 2 条
[5] 审核通过，建立 Club #4 并授予申请人该社团 R02
[6] student02 的 /auth/me 已出现新社团 R02 授权
[7] 年审提交/驳回成功；驳回只改年审记录，未冻结社团
[8] 入团申请处理成功，成员关系为 ACTIVE
[9] 负责人可查看完整名册，共 2 人

ALL PASS：M02/M03 端到端联调通过
```

### 4.3 数据库落库核对

浏览器验收后直接查询 MySQL：

| 核对项 | 实际结果 |
|---|---|
| 注册申请 → Club | 浏览器验收申请 `#8` → `APPROVED` → 建立 Club `#5` |
| 申请人 R02 | `student02` 在 Club `#5` 有 `R02` 授权 |
| 年审 | `annual_review_applications` 中 `review_year=2099`、`review_status=REJECTED`、保留审核意见 |
| 成员关系 | `student02` 为 Club `#5` 负责人；`student01` 为 `ACTIVE`，职务“浏览器验收职务” |
| 审计 | `CLUB_REGISTRATION_CREATE/SUBMIT/REVIEW`、`ANNUAL_REVIEW_CREATE/SUBMIT/REVIEW`、`MEMBERSHIP_JOIN_APPLY/PROCESS`、`CLUB_MEMBER_POSITION_UPDATE` 均落库 |
| 通知 | `CLUB_REGISTRATION_*`、`ANNUAL_REVIEW_*`、`MEMBERSHIP_APPLICATION_*` 事件均生成 |

真实 SQL 的 M07-A 统计：

```text
R03 scope ALL      clubs=5 active=4 memberships=8 pending=0
R02 scope OWN_CLUBS clubs=2 club_ids=[5, 4]
R01 denied         40301
```

真实错误路径：

```text
重复年审 same club/year      HTTP 409 / code 40902
student02 修改 Club 1 资料   HTTP 403 / code 40302
manager01 打开 Club 5 名册   HTTP 403 / code 40302
```

### 4.4 复现命令（Docker 可用时）

```powershell
cd D:\软件\ruanjian-main
docker compose up -d mysql
cd backend
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

另开终端：

```powershell
cd D:\软件\ruanjian-main\backend
.\.venv\Scripts\python.exe ..\..\成员A\integration\smoke_m02_m03.py
```

本轮因无 Docker，实际使用便携 MySQL 8.4.11；命令与连接串相应改为 `127.0.0.1:3307`。

## 5. 前端构建

```powershell
cd D:\软件\ruanjian-main\frontend
npm.cmd install
npm.cmd run build
```

实际输出：

```text
vite v7.3.6 building client environment for production...
✓ 110 modules transformed.
dist/index.html                   0.42 kB
dist/assets/index-<hash>.css      约 7.05 kB
dist/assets/index-<hash>.js       约 183 kB
✓ built in 约 0.8s
```

> 产物 hash 随每次构建变化，上表只保留体积与模块数。

### 5.1 构建覆盖

- `ClubsView.vue`：注册申请、审核、社团资料、年审四个区域；
- `MembersView.vue`：申请列表/处理、名册/职务；
- `api/clubs.js`、`api/members.js` 只封装现有 URL，不新增路由。

### 5.2 浏览器验收（已执行）

使用 Chrome 156.0.8078.48 + Playwright Core 1.64.1，在真实 MySQL 后端上执行 9 步流程，全部通过：

1. student02 创建并提交注册申请；
2. manager01 审核通过；
3. student02 刷新身份，首页出现新社团 R02；
4. student02 创建并提交 2099 年审；
5. manager01 驳回年审，社团未被冻结；
6. student01 提交入团申请；
7. student02 同意入团；
8. student02 查看名册并维护职务；
9. manager01（R03）打开名册被拒绝（403）。

截图与详细结果见 [`REAL_DB_AND_BROWSER_ACCEPTANCE.md`](REAL_DB_AND_BROWSER_ACCEPTANCE.md) 和 [`screenshots/`](screenshots/)。

验收过程中没有未捕获 JS 错误、没有 5xx；浏览器控制台出现预期的 favicon 404 和 R03 名册 403 网络错误。

## 6. 风险与后续

| 风险 | 影响 | 建议 |
|---|---|---|
| Docker Desktop 未安装 | 本轮用便携 MySQL 8.4.11 验证，不是 Docker 容器环境 | 如需完全按 README，安装 Docker Desktop/WSL2 后重跑 compose |
| 年审重新提交规则未定 | 被驳回的年度无法新建同年度申请 | 负责人按 EI-A-02 决策；必要时走 CR |
| R03 对 M03 全量范围未定 | 当前按契约拒绝 R03 全量访问 | 负责人按 EI-A-03 决策 |
| 通知/审计表由多人写入 | 字段语义或查询过滤可能不一致 | 与 M06/M07 owner 对齐 `event_type`/`action` 命名 |
| 浏览器验收为 headless 自动化 | 未覆盖人工视觉/可访问性细节 | 演示前人工看一遍截图与页面 |
| 测试数据为本地虚构数据 | 不能当作真实学校数据 | 课程报告中说明数据来源 |
