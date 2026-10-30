# 真实 MySQL 联调与浏览器验收报告

> 执行日期：2026-10-30
> 项目：高校社团活动管理系统（课程工程 Skeleton V0.1）
> 范围：成员 A 的 M02 / M03 / M07-A

## 1. 结论

| 项目 | 结果 |
|---|---|
| 真实 MySQL 8.4.11 数据库 | **PASS** |
| Alembic migration + seed | **PASS** |
| 后端 `/api/v1/health` | **PASS** |
| M02/M03 端到端 smoke | **PASS** |
| M07-A 真实 SQL 统计 | **PASS** |
| 真实错误路径（40902 / 40302） | **PASS** |
| 浏览器 E2E（Chrome 156 + Playwright） | **PASS** |
| 截图证据 | **9 张** |

**重要偏差**：本轮**没有使用 Docker Desktop**。当前 Windows 用户不是管理员，且未安装 WSL2，Docker Desktop 无法安装；因此改用**便携版 MySQL 8.4.11**（与 `docker-compose.yml` 的 `mysql:8.4` 同属 8.4，服务端版本 8.4.11）完成真实数据库联调。Docker 容器本身未被验证。

## 2. 环境

| 组件 | 版本/位置 |
|---|---|
| OS | Windows（当前用户 Medium integrity，非管理员） |
| Python | 3.12.6，`D:\python\python3.12.6\python.exe` |
| 后端依赖 | FastAPI 0.162.0、SQLAlchemy 2.0.55、PyMySQL、pytest 8.4.2 |
| MySQL | 8.4.11 Community Server，便携 ZIP，`D:\mysql84`，端口 **3307** |
| 数据库 | `club_management`，用户 `club_app` |
| Node | 22.12.0 便携版，`D:\node22` |
| 前端 | Vite 7.3.6，`127.0.0.1:5173` |
| 浏览器 | Chrome 156.0.8078.48 |
| 自动化 | Playwright Core 1.64.1（使用系统 Chrome，无额外下载浏览器） |
| 后端 API | `127.0.0.1:8000` |

> 端口使用 3307 而不是 3306，避免与本机可能存在的 MySQL 冲突；验证副本的 `backend/.env` 指向 3307。

## 3. 真实 MySQL 联调

### 3.1 数据库初始化

```powershell
# 便携 MySQL 8.4.11
D:\mysql84\bin\mysqld.exe --initialize-insecure --basedir=D:\mysql84 --datadir=D:\mysql84\data
D:\mysql84\bin\mysqld.exe --basedir=D:\mysql84 --datadir=D:\mysql84\data --port=3307 --bind-address=127.0.0.1 --mysqlx=0
```

创建数据库和应用账号：

```sql
CREATE DATABASE club_management CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'club_app'@'127.0.0.1' IDENTIFIED BY 'club_app';
GRANT ALL PRIVILEGES ON club_management.* TO 'club_app'@'127.0.0.1';
```

### 3.2 Migration 与 Seed

```powershell
cd D:\软件\.verify_memberA\project\backend
D:\软件\.verify_memberA\.venv\Scripts\python.exe -m alembic upgrade head
D:\软件\.verify_memberA\.venv\Scripts\python.exe -m app.db.seed
```

实际输出：

```text
INFO  [alembic.runtime.migration] Running upgrade  -> 20260915_0001, V0.1 initial schema for MySQL 8.
Seed completed: 6 users, 3 clubs, applications, activities, finance records and notifications.
```

验证表数量：

```text
15 张物理表 = 14 张业务表 + alembic_version
```

### 3.3 健康检查

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/v1/health
```

```json
{"code":0,"message":"success","data":{"service":"up","database":"up"}}
```

### 3.4 端到端 smoke

```powershell
cd D:\软件\.verify_memberA\project\backend
$env:API_BASE='http://127.0.0.1:8000/api/v1'
D:\软件\.verify_memberA\.venv\Scripts\python.exe D:\软件\成员A\integration\smoke_m02_m03.py
```

实际输出：

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

### 3.5 数据库落库核对

浏览器验收创建的社团为 `成员A浏览器验收社团20261030111420`（Club `#5`，注册申请 `#8`）。

| 核对项 | MySQL 实际结果 |
|---|---|
| 注册申请 → Club | 申请 `#8` 状态 `APPROVED`，建立 Club `#5` |
| 申请人 R02 | `student02` 在 Club `#5` 有 `R02` 授权 |
| 年审 | 年审 `#6`，`review_year=2099`，`review_status=REJECTED`，审核意见已保存 |
| 成员关系 | `student02`（负责人）、`student01`（`ACTIVE`，职务“浏览器验收职务”） |
| 审计 | 注册创建/提交/审核、年审创建/提交/审核、入团申请/处理、职务更新均有记录 |
| 通知 | 注册、年审、成员申请事件均生成站内通知 |

审计日志尾部：

```text
CLUB_MEMBER_POSITION_UPDATE   club_member                 8
MEMBERSHIP_APPLICATION_PROCESS membership_application     2
MEMBERSHIP_JOIN_APPLY          membership_application     2
ANNUAL_REVIEW_REVIEW          annual_review_application   6
ANNUAL_REVIEW_SUBMIT          annual_review_application   6
ANNUAL_REVIEW_CREATE          annual_review_application   6
CLUB_REGISTRATION_REVIEW      club_registration_application 8
CLUB_REGISTRATION_SUBMIT      club_registration_application 8
CLUB_REGISTRATION_CREATE      club_registration_application 8
```

通知事件：

```text
CLUB_REGISTRATION_SUBMITTED / APPROVED
ANNUAL_REVIEW_SUBMITTED / REJECTED
MEMBERSHIP_APPLICATION_SUBMITTED / APPROVED
```

### 3.6 M07-A 真实 SQL 统计

直接调用 `club_member_statistics()`：

```text
R03 scope ALL       clubs=5 active=4 memberships=8 pending=0
R02 scope OWN_CLUBS clubs=2 club_ids=[5, 4]
R01 denied          40301
```

说明：

- R03 能看到全部 5 个社团；
- R02（student02）只看到自己负责的 Club 5、Club 4；
- R01 被拒绝；
- `GROUP BY`、`COUNT(DISTINCT)`、年审状态关联在真实 MySQL 上执行正常。

### 3.7 真实错误路径

| 场景 | 实际结果 |
|---|---|
| student02 对已存在年审的 Club 5 / 2099 再次创建 | HTTP 409 / code 40902 |
| student02 修改 Club 1（非本人负责） | HTTP 403 / code 40302 |
| manager01（R03）打开 Club 5 名册 | HTTP 403 / code 40302 |

## 4. 浏览器验收

### 4.1 启动

```powershell
# 后端
cd D:\软件\.verify_memberA\project\backend
D:\软件\.verify_memberA\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 前端
cd D:\软件\.verify_memberA\project\frontend
D:\node22\node-v22.12.0-win-x64\npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

### 4.2 流程与结果

| 步骤 | 操作 | 结果 |
|---|---|---|
| 1 | student02 创建注册申请并提交 | PASS，状态 DRAFT → PENDING |
| 2 | manager01 审核通过 | PASS，建立 Club + R02 |
| 3 | student02 刷新身份 | PASS，首页出现新社团 R02 |
| 4 | student02 创建/提交 2099 年审 | PASS，DRAFT → PENDING |
| 5 | manager01 驳回年审 | PASS，REJECTED，社团未冻结 |
| 6 | student01 提交入团申请 | PASS |
| 7 | student02 同意入团 | PASS，成员关系 ACTIVE |
| 8 | student02 查看名册并维护职务 | PASS，职务保存成功 |
| 9 | manager01（R03）打开名册 | PASS，正确显示 403 拒绝信息 |

自动化断言：

- 无未捕获 JS `pageerror`；
- 无 HTTP 5xx；
- 预期内的网络错误只有 favicon 404 和 R03 名册 403；
- 每一步均等待页面成功提示或目标行出现。

自动化输出：

```text
{
  "clubName": "成员A浏览器验收社团20261030111420",
  "screenshots": [
    "01-注册申请已提交.png",
    "02-注册审核通过.png",
    "03-申请人获得R02授权.png",
    "04-年审已提交.png",
    "05-年审驳回且社团未冻结.png",
    "06-入团申请已提交.png",
    "07-入团申请已同意.png",
    "08-成员名册与职务.png",
    "09-R03名册越权被拒绝.png"
  ]
}
BROWSER ACCEPTANCE PASS
```

### 4.3 截图

| 截图 | 内容 |
|---|---|
| [01-注册申请已提交.png](screenshots/01-注册申请已提交.png) | 注册申请待审核 |
| [02-注册审核通过.png](screenshots/02-注册审核通过.png) | R03 审核通过 |
| [03-申请人获得R02授权.png](screenshots/03-申请人获得R02授权.png) | 首页出现新社团 R02 |
| [04-年审已提交.png](screenshots/04-年审已提交.png) | 年审待审核 |
| [05-年审驳回且社团未冻结.png](screenshots/05-年审驳回且社团未冻结.png) | 年审驳回 |
| [06-入团申请已提交.png](screenshots/06-入团申请已提交.png) | 入团申请待处理 |
| [07-入团申请已同意.png](screenshots/07-入团申请已同意.png) | 成员关系已同步 |
| [08-成员名册与职务.png](screenshots/08-成员名册与职务.png) | 名册与职务维护 |
| [09-R03名册越权被拒绝.png](screenshots/09-R03名册越权被拒绝.png) | R03 名册 403 |

## 5. 复现方式

### 5.1 Docker 可用时（原计划）

```powershell
cd D:\软件\ruanjian-main
docker compose up -d mysql
cd backend
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

### 5.2 本轮实际环境（便携 MySQL）

```powershell
# 1. MySQL
D:\mysql84\bin\mysqld.exe --basedir=D:\mysql84 --datadir=D:\mysql84\data --port=3307 --bind-address=127.0.0.1 --mysqlx=0

# 2. 后端
cd D:\软件\.verify_memberA\project\backend
D:\软件\.verify_memberA\.venv\Scripts\python.exe -m alembic upgrade head
D:\软件\.verify_memberA\.venv\Scripts\python.exe -m app.db.seed
D:\软件\.verify_memberA\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3. 前端
cd D:\软件\.verify_memberA\project\frontend
D:\node22\node-v22.12.0-win-x64\npm.cmd install
D:\node22\node-v22.12.0-win-x64\npm.cmd run dev -- --host 127.0.0.1 --port 5173

# 4. 浏览器验收
cd D:\软件\.verify_memberA\browser
$env:PATH='D:\node22\node-v22.12.0-win-x64;' + $env:PATH
npm.cmd install --registry=https://registry.npmmirror.com playwright-core
node acceptance.js
```

## 6. 限制

1. **Docker Desktop 未验证**：当前用户无管理员权限，WSL2 未安装。真实 MySQL 验证成立，但“容器运行 MySQL”这一层没有验证。
2. **测试数据是虚构的**：所有社团、申请、年审、成员均为验收数据，不代表真实学校制度。
3. **浏览器验收为 headless 自动化**：覆盖主流程和关键越权，不替代人工视觉、响应式、可访问性检查。
4. **本地服务仍运行**：MySQL 3307、后端 8000、前端 5173；如需停止，见第 7 节。

## 7. 停止与清理

```powershell
# 停止前端/后端：结束监听 5173 / 8000 的进程
Get-NetTCPConnection -State Listen -LocalPort 5173,8000 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }

# 停止 MySQL
D:\mysql84\bin\mysqladmin.exe -h 127.0.0.1 -P 3307 -u root shutdown

# 可选：删除验证数据库文件（会丢失本轮验收数据）
# Remove-Item -Recurse -Force D:\mysql84\data
```

> `D:\mysql84`、`D:\node22`、`.verify_memberA` 都是本轮验证环境，不属于 `成员A` 交付源码；`成员A/docs/screenshots/` 是本轮浏览器验收的可提交证据。
