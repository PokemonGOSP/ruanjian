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
  - 集成 M04 后完整 `pytest`：30 passed；集成 M02/M03 后：71 passed。
  - `ruff check app/api/v1/accounts.py`：仅 1 项 F401 未使用导入，已修复；`app/db/seed.py`、`app/db/models/domain.py`、`tests/test_auth.py` 的 lint 欠账为既有问题，另行处理。
- REQUIRES_CR：否。该问题不改变角色、FR、接口语义或数据模型。

## EI-04：本机 Docker Hub 不可达、缺少 MySQL，M04～M07 真实数据库集成验证待执行

- 类型：环境/网络问题
- 状态：`OPEN`
- 发现时间：2026-10-28（成员 B 记录 M04 部分，成员 C 补充 M05/M06/M07 部分，集成时合并）
- 现象：`docker images` 为空；`docker pull mysql:8.4` 访问 `registry-1.docker.io:443` 超时；本机未安装 MySQL 服务，无法执行 `alembic upgrade head`、`python -m app.db.seed` 和真实接口联调。
- 影响：
  - M04：Service/状态机/权限/通知由 11 个 pytest 用例覆盖（内存 Repository 替身），SQL 已按 MySQL 方言编译检查。
  - M05/M06/M07：成员 C 与既有单元/接口测试通过；OpenAPI 生成和前端构建通过。
  - 三个模块的真实 migration + seed + DB 端到端联调均未在本机执行。
- 处理建议：在具备 MySQL 8 或可拉取镜像的环境执行 `docker compose up -d mysql`、`alembic upgrade head`、`python -m app.db.seed`，再按 `docs/development/M04_ACTIVITY.md` 第 7 节及各模块实现文档复验。
- REQUIRES_CR：否。

## EI-05：请求参数校验错误响应无法序列化

- 类型：公共异常处理缺陷
- 状态：`RESOLVED`
- 发现时间：2026-10-27（成员 C）
- 现象：`RequestValidationError.errors()` 的 `ctx` 中可能包含 `ValueError` 或 `Decimal`，原 `JSONResponse` 直接序列化时抛 `TypeError`，导致本应返回 422/40001 的请求变成 500。
- 触发场景：成员 C 的经费金额校验（如 `amount=0`）、自定义 Pydantic validator 失败时。
- 处理：在 `app/core/exceptions.py` 中移除不可序列化的 `ctx`，并使用 `jsonable_encoder` 编码错误数据；响应结构仍为 `{code,message,data}`，错误码不变。
- 影响：所有模块的参数校验错误响应；按公共异常处理变更规则由负责人复核。
- 复核结论（2026-10-30）：变更仅影响错误响应序列化，不改变响应结构、错误码或权限语义；合并后相关测试通过。
- REQUIRES_CR：否。

## 结论

- 未发现需求层矛盾，不存在 `REQUIRES_CR`。
- EI-01、EI-02、EI-03、EI-05 已解除；EI-04 为当前机器 Docker/网络限制，需在具备 MySQL 8 的环境补做 M04～M07 端到端集成验证。
