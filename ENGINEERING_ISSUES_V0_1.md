# Engineering Issues V0.1

> 记录日期：2026-09-21
> 需求基线：`REQUIREMENTS_BASELINE_V1_1.md`

## EI-01：Windows 主机 Python 启动入口不可用

- 类型：环境缺失
- 状态：`MITIGATED_BY_WSL`
- 现象：Windows `python --version` 不可用；WSL Python 3.12.3 可用。
- 处理：使用 WSL 临时 venv 完成依赖安装、真实迁移、Seed、pytest 和服务验证。
- REQUIRES_CR：否。

## EI-02：MySQL 8 镜像/数据卷初始化阻塞

- 类型：环境/初始化问题
- 状态：`RESOLVED`
- 原因：首次拉取较慢且旧 data volume 初始化损坏，日志出现 `Cannot create redo log files` 与 `Data Dictionary initialization failed`。
- 处理：人工执行 `docker compose down -v` 清理损坏 volume，再执行 `docker compose up -d` 重新初始化。
- 验证：`mysql:8.4`（Server 8.4.11）容器 healthy；真实 Alembic migration、Seed、health、login、`/auth/me` 和集成验证均通过。
- REQUIRES_CR：否。

## EI-03：M01 自动化测试环境依赖未就绪

- 类型：本地开发/验证环境问题
- 状态：`RESOLVED`
- 发现时间：2026-10-26
- 现象：当时 Windows Python 3.12 与 WSL Python 3.12 均未安装 `pytest`、`ruff` 及项目运行依赖；按现有 `backend/requirements.txt` 启动安装时仅完成部分下载元数据，未形成可用环境。
- 影响范围：`feature/m01-auth` 的 6 个 FR-23 账号/授权 endpoint 已完成代码与测试用例编写，但完整 `pytest` 和 `ruff` 当时尚未实际执行。
- 处理：使用 `backend/.venv`（Python 3.12.6，pytest 8.4.2，ruff 0.17.2）执行验证。
- 验证（2026-10-30）：
  - `pytest tests/test_accounts.py -q`：15 passed（覆盖 6 个 FR-23 endpoint 的正向/权限/异常路径）。
  - 合并 `main`（M04）后完整 `pytest`：30 passed。
  - `ruff check app/api/v1/accounts.py`：仅 1 项 F401 未使用导入，已修复；`app/db/seed.py`、`app/db/models/domain.py`、`tests/test_auth.py` 的 lint 欠账为 main 既有问题，另行处理。
- REQUIRES_CR：否。该问题不改变角色、FR、接口语义或数据模型。

## EI-04：本机 Docker Hub 不可达，M04 真实 MySQL 集成验证待执行

- 类型：环境/网络问题
- 状态：`OPEN`
- 发现时间：2026-10-28
- 现象：`docker images` 为空；`docker pull mysql:8.4` 访问 `registry-1.docker.io:443` 超时，无法准备 MySQL 8 容器；本机未安装 MySQL 服务。
- 影响：M04 的 Service/状态机/权限/通知由 11 个 pytest 用例覆盖（内存 Repository 替身），SQL 已按 MySQL 方言编译检查；但 migration + seed + 真实 DB 的端到端联调未在本机执行。
- 处理建议：在具备 MySQL 8 或可拉取镜像的环境执行 `docker compose up -d mysql`、`alembic upgrade head`、`python -m app.db.seed`，再按 `docs/development/M04_ACTIVITY.md` 第 7 节复验。
- REQUIRES_CR：否。

## 结论

- 未发现需求层矛盾，不存在 `REQUIRES_CR`。
- EI-01、EI-02、EI-03 已解除；EI-04 为当前机器 Docker 网络限制，需在具备 MySQL 8 的环境补做 M04 端到端集成验证。
