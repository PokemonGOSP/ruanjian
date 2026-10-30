# 高校社团活动管理系统 — Engineering Skeleton V0.1

基于 `REQUIREMENTS_BASELINE_V1_1.md` 的课程工程。已跑通本地测试账号登录、JWT、`/auth/me` 和前端认证状态，并实现 M01 账号与角色授权（FR-23，含账号管理页面）、M02/M03 社团与成员管理（FR-03～FR-10）、M04 活动管理（FR-11～FR-16）、M05 经费（FR-17～FR-18）、M06 通知（FR-19～FR-20）、M07 统计与审计（FR-21～FR-22，含 M07-A 社团/成员统计）。已在真实 MySQL 8.4 上完成 migration、Seed 和 M01～M07 端到端联调。

## 技术栈

- Vue 3 + Vite + JavaScript + Vue Router + Pinia + Axios
- Python 3.11+ + FastAPI + SQLAlchemy 2.x + Pydantic + Alembic + PyJWT + pytest
- MySQL 8（不能替换为 SQLite）

## 目录

```text
backend/    FastAPI、SQLAlchemy、Alembic、tests
frontend/   Vue/Vite SPA
database/   MySQL 参考 Schema、Seed 和说明
docs/       Requirements 引用、API、架构和 ownership
```

## 环境要求

- Python 3.11 或更高版本
- Node.js 20.19+ 或 22.12+（本机检查到 Node 24.16.0）
- MySQL 8，或 Docker Desktop / Docker Engine + Compose

## Windows 启动

```powershell
Copy-Item .env.example .env
docker compose up -d mysql

cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

另开终端：

```powershell
cd frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

如果 PowerShell 禁止 `npm.ps1`，使用 `npm.cmd`。若虚拟环境激活脚本也被策略阻止，可直接运行 `.\.venv\Scripts\python.exe -m pip ...`。

## WSL/Linux 启动

```bash
cp .env.example .env
docker compose up -d mysql
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

另开终端：

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

## 普通 MySQL（无 Docker）

1. 在 MySQL 8 创建数据库和本地账号，或执行 `database/schema.sql`。
2. 将 `backend/.env` 的 `DATABASE_URL` 改成本机 MySQL 连接串。
3. 推荐仍从空数据库执行 `alembic upgrade head`，再运行 `python -m app.db.seed`。

不得为了临时通过测试把配置改成 SQLite。

## Migration 与 Seed

```powershell
cd backend
alembic upgrade head
python -m app.db.seed
```

空库 migration 会创建 14 张表。Seed 数据完全虚构，包含 6 个账号、3 个社团、申请/活动状态样例、经费和通知。

## 本地测试账号

| 用途 | 用户名 | 密码 | 权限 |
|---|---|---|---|
| 普通学生 | `student01` | `Student123!` | R01 |
| 社团负责人 | `leader01` | `Leader123!` | R01 + 指定社团 R02 |
| 业务管理员 | `manager01` | `Manager123!` | R01 + R03 |
| 系统管理员 | `admin01` | `Admin123!` | R01 + R04 |

凭据只用于本地开发，不得部署到公开环境。

## 测试与构建

```powershell
cd backend
pytest
# 可选静态检查（先执行 pip install ruff）
ruff check app tests

cd ..\frontend
npm.cmd install
npm.cmd run build
```

## 地址

- Frontend：<http://localhost:5173>
- API docs：<http://127.0.0.1:8000/docs>
- Health：<http://127.0.0.1:8000/api/v1/health>
- API prefix：`/api/v1`

## Ownership

团队统一阅读入口：`docs/team/README.md`。其中按全员、负责人、成员 A/B/C 分类列出正式需求基线、工程封装、API 契约、验收记录和操作命令。

- Leader / Integration：M01、公共层、Migration、Seed、集成和 CR
- Member A：M02、M03
- Member B：M04
- Member C：M05、M06、M07

详细规则见 `docs/development/MODULE_OWNERSHIP.md`。

## 当前实现范围

已实现：health、login、logout、me、统一异常/响应、JWT/PBKDF2、SQLAlchemy 模型、Alembic、Seed、前端登录与 Dashboard 认证状态。

- M01（FR-23）：账号与角色授权 6 个 endpoint（列表、创建、启停、授予 R02/R03/R04、撤销系统角色、撤销社团 R02）及账号管理页面；
- M02/M03（FR-03～FR-10）：社团注册与年审、入团/退出申请处理、成员名册与职务；
- M04（FR-11～FR-16）：活动申报、审核、发布、报名、取消/归档，含状态机与站内通知；
- M05（FR-17～FR-18）：经费记录登记、修改、作废、查询与汇总；
- M06（FR-19～FR-20）：站内通知列表、已读和管理通知发布；
- M07：社团/成员统计（M07-A）、综合统计（含活动/报名统计；M07-B 无独立 endpoint，由 `/reports/summary` 覆盖）、经费 CSV 导出和 R04 审计日志查询（FR-21、FR-22）。

各模块实现说明见 `docs/development/M01_ACCOUNTS.md`、`docs/development/M04_ACTIVITY.md`、`docs/development/M05_M06_M07_IMPLEMENTATION.md` 和 `docs/member-a/`。路由契约见 `docs/api/API_CONTRACT_V0_1.md`。

## 当前 TODO

- 无阻塞 TODO；后续需求变更按 `ENGINEERING_ISSUES_V0_1.md` 的流程记录。

环境实测结果见 `ENGINEERING_VALIDATION_V0_1.md`；环境或需求问题见 `ENGINEERING_ISSUES_V0_1.md`。
