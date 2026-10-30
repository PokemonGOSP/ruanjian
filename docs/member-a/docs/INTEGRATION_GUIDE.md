# 成员 A 集成指南

> 目标：把 `成员A/` 中的文件合并进 `ruanjian-main/`，不改变公共模型、Migration、路由基础结构和 API 契约。
> 本文中的命令以仓库根目录 `ruanjian-main/` 为参照；`成员A/` 与 `ruanjian-main/` 同级。

## 1. 文件映射

### 1.1 新增文件（直接复制）

```text
成员A/backend/app/schemas/club.py                  -> ruanjian-main/backend/app/schemas/club.py
成员A/backend/app/schemas/member.py                -> ruanjian-main/backend/app/schemas/member.py
成员A/backend/app/schemas/statistics.py            -> ruanjian-main/backend/app/schemas/statistics.py
成员A/backend/app/repositories/club_repository.py  -> ruanjian-main/backend/app/repositories/club_repository.py
成员A/backend/app/repositories/member_repository.py-> ruanjian-main/backend/app/repositories/member_repository.py
成员A/backend/app/services/club_service.py         -> ruanjian-main/backend/app/services/club_service.py
成员A/backend/app/services/member_service.py       -> ruanjian-main/backend/app/services/member_service.py
成员A/backend/app/services/club_member_events.py   -> ruanjian-main/backend/app/services/club_member_events.py
成员A/backend/app/services/club_member_statistics.py -> ruanjian-main/backend/app/services/club_member_statistics.py
成员A/backend/tests/conftest.py                    -> ruanjian-main/backend/tests/conftest.py
成员A/backend/tests/helpers.py                     -> ruanjian-main/backend/tests/helpers.py
成员A/backend/tests/__init__.py                    -> ruanjian-main/backend/tests/__init__.py
成员A/backend/tests/test_m02_*.py                  -> ruanjian-main/backend/tests/
成员A/backend/tests/test_m03_members.py            -> ruanjian-main/backend/tests/
成员A/backend/tests/test_m07a_statistics.py        -> ruanjian-main/backend/tests/
成员A/frontend/src/api/clubs.js                    -> ruanjian-main/frontend/src/api/clubs.js
成员A/frontend/src/api/members.js                  -> ruanjian-main/frontend/src/api/members.js
成员A/frontend/src/utils/m02m03.js                 -> ruanjian-main/frontend/src/utils/m02m03.js
```

### 1.2 替换文件

```text
成员A/backend/app/api/v1/clubs.py          -> ruanjian-main/backend/app/api/v1/clubs.py
成员A/backend/app/api/v1/annual_reviews.py -> ruanjian-main/backend/app/api/v1/annual_reviews.py
成员A/backend/app/api/v1/members.py        -> ruanjian-main/backend/app/api/v1/members.py
成员A/frontend/src/views/ClubsView.vue     -> ruanjian-main/frontend/src/views/ClubsView.vue
成员A/frontend/src/views/MembersView.vue   -> ruanjian-main/frontend/src/views/MembersView.vue
```

### 1.3 不修改的文件

以下文件保持原样，确保公共层不被成员 A 私自改动：

```text
backend/app/db/models/domain.py
backend/app/db/seed.py
backend/app/api/deps.py
backend/app/api/v1/__init__.py
backend/app/core/*.py
backend/app/schemas/common.py
backend/app/schemas/business.py
backend/alembic/**
database/schema.sql
frontend/src/router/index.js
frontend/src/components/AppLayout.vue
frontend/src/api/client.js
frontend/src/stores/auth.js
frontend/package.json
```

因此：

- 不需要新增 Alembic migration；现有 14 张业务表已覆盖 M02/M03。
- 不需要新增前端路由；`/clubs`、`/members` 已存在。
- 不需要新增依赖；前端只使用 Vue/Axios，后端只使用 FastAPI/SQLAlchemy/Pydantic。
- 不改变 API Contract 的任何 URL 或 method。

## 2. 合并命令（PowerShell 示例）

```powershell
$repo = "D:\软件\ruanjian-main"
$out  = "D:\软件\成员A"

# 新增文件
Copy-Item "$out\backend\app\schemas\club.py" "$repo\backend\app\schemas\club.py"
Copy-Item "$out\backend\app\schemas\member.py" "$repo\backend\app\schemas\member.py"
Copy-Item "$out\backend\app\schemas\statistics.py" "$repo\backend\app\schemas\statistics.py"
Copy-Item "$out\backend\app\repositories\club_repository.py" "$repo\backend\app\repositories\club_repository.py"
Copy-Item "$out\backend\app\repositories\member_repository.py" "$repo\backend\app\repositories\member_repository.py"
Copy-Item "$out\backend\app\services\club_service.py" "$repo\backend\app\services\club_service.py"
Copy-Item "$out\backend\app\services\member_service.py" "$repo\backend\app\services\member_service.py"
Copy-Item "$out\backend\app\services\club_member_events.py" "$repo\backend\app\services\club_member_events.py"
Copy-Item "$out\backend\app\services\club_member_statistics.py" "$repo\backend\app\services\club_member_statistics.py"
Copy-Item "$out\backend\tests\*.py" "$repo\backend\tests\"

# 替换文件
Copy-Item -Force "$out\backend\app\api\v1\clubs.py" "$repo\backend\app\api\v1\clubs.py"
Copy-Item -Force "$out\backend\app\api\v1\annual_reviews.py" "$repo\backend\app\api\v1\annual_reviews.py"
Copy-Item -Force "$out\backend\app\api\v1\members.py" "$repo\backend\app\api\v1\members.py"
Copy-Item -Force "$out\frontend\src\api\clubs.js" "$repo\frontend\src\api\clubs.js"
Copy-Item -Force "$out\frontend\src\api\members.js" "$repo\frontend\src\api\members.js"
Copy-Item -Force "$out\frontend\src\utils\m02m03.js" "$repo\frontend\src\utils\m02m03.js"
Copy-Item -Force "$out\frontend\src\views\ClubsView.vue" "$repo\frontend\src\views\ClubsView.vue"
Copy-Item -Force "$out\frontend\src\views\MembersView.vue" "$repo\frontend\src\views\MembersView.vue"
```

> 建议在 `feature/m02-m03-club-member` 分支执行，提交前运行第 3 节检查。

## 3. 合并后验证

### 3.1 后端单元/契约测试

```powershell
cd D:\软件\ruanjian-main\backend
.\.venv\Scripts\python.exe -m pytest -q
# 期望：45 passed（含原 4 个测试 + 成员 A 41 个测试）
.\.venv\Scripts\python.exe -m ruff check app tests
```

> 若本地 venv 尚未安装 `ruff`，先执行 `pip install ruff`；或只对成员 A 文件执行。

### 3.2 真实 MySQL 链路（必须执行，不能用 SQLite 替代）

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

期望最后输出：

```text
ALL PASS：M02/M03 端到端联调通过
```

> 2026-10-30 已在便携 MySQL 8.4.11 上实测通过；本机因无管理员权限/WSL2，Docker 容器本身未验证，证据见 `docs/REAL_DB_AND_BROWSER_ACCEPTANCE.md`。

该脚本会：

1. 登录 4 个 seed 账号；
2. student02 创建并提交社团注册申请；
3. manager01 审核通过，验证建立 Club 并授予申请人该社团 R02；
4. student02 的 `/auth/me` 出现新社团授权；
5. student02 创建/提交年审，manager01 驳回，验证只改年审记录；
6. student01 申请入团，student02 处理同意，验证成员关系 `ACTIVE`；
7. student02 查看完整名册。

### 3.3 前端构建

```powershell
cd D:\软件\ruanjian-main\frontend
npm.cmd install
npm.cmd run build
# 期望：vite build 成功，110 modules transformed
```

### 3.4 手工 UI 冒烟

启动后端和前端后，按 [`ACCEPTANCE_CHECKLIST.md`](ACCEPTANCE_CHECKLIST.md) 操作：

- student01 登录 → 社团/年审 → 新建注册申请 → 提交；
- manager01 登录 → 社团/年审 → 审核通过；
- student01 重新登录/刷新身份 → 首页出现新社团 R02；
- student02 登录 → 成员 → 申请入团 → 切换“我负责社团的申请”处理；
- leader01 登录 → 社团/年审 → 编辑社团资料、创建年审、提交；
- manager01 驳回年审 → 验证社团/其他业务未被冻结。

### 3.5 浏览器自动化（可选）

需要 Node.js、系统 Chrome 和 `playwright-core`：

```powershell
cd D:\软件\成员A\integration
npm.cmd install playwright-core --registry=https://registry.npmmirror.com

$env:APP_BASE='http://127.0.0.1:5173'
$env:CHROME_PATH='C:\Program Files\Google\Chrome\Application\chrome.exe'
# 可选：自定义截图目录
# $env:SCREENSHOTS_DIR='D:\软件\成员A\docs\screenshots'
node browser_acceptance.js
```

期望最后输出 `BROWSER ACCEPTANCE PASS`，并在 `docs/screenshots/` 生成 9 张截图。

## 4. 合并冲突与处理

| 冲突点 | 原因 | 处理 |
|---|---|---|
| `clubs.py`、`annual_reviews.py`、`members.py` 被其他人改过 | 这三个文件是 Skeleton 占位，成员 A 必须替换 | 以本交付为准；如他人新增了契约，先核对 API Contract 再合并 |
| `app/api/v1/__init__.py` | 本交付未改；若他人改了 import 顺序 | 保留他人版本，只需保证 routers 仍被 include |
| `schemas/business.py` 的 `PayloadRequest` | 本交付未改；新 Schema 独立文件 | 不需要改公共 Schema |
| 前端 `ClubsView.vue` / `MembersView.vue` | 本交付替换占位页 | 若他人也在改，按页面整体替换；路由和导航不变 |
| 通知/审计表由 M06/M07 使用 | 本交付只写 `notifications`/`audit_logs` | 不合并 M06/M07 的 Service；双方都写同一张表不冲突，字段语义见实现说明 |
| M07-A 统计被加到 `reports.py` | 本交付不提供路由 | 由 M07 owner 按 `integration/reports_m07a_snippet.py` 组合 |

## 5. 回滚

本交付不涉及 Migration，回滚只需：

```powershell
git checkout -- backend/app/api/v1/clubs.py backend/app/api/v1/annual_reviews.py backend/app/api/v1/members.py
git checkout -- frontend/src/views/ClubsView.vue frontend/src/views/MembersView.vue
# 删除新增文件（按 1.1 列表）
```

## 6. 已知限制

- **Docker Desktop 未验证**：本机当前用户无管理员权限、未安装 WSL2，Docker Desktop 无法安装；真实联调使用便携 MySQL 8.4.11，Docker 容器本身未验证。
- 年审驳回后的重新提交规则未在基线细化；当前实现遵循契约的“只有草稿/已撤回可编辑”和 `(club_id, review_year)` 唯一约束，见 `ENGINEERING_NOTES.md` EI-A-02。
- R03 对 M03 申请/名册的全量访问未实现，理由与待确认项见 EI-A-03。
- 浏览器验收为 headless Chrome 自动化，覆盖主流程和关键越权；不替代人工视觉、响应式和无障碍检查。
- 本轮验证数据为本地虚构数据，不代表真实学校制度。
