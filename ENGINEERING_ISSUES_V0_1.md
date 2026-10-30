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
- 状态：`RESOLVED`
- 发现时间：2026-10-28（成员 B 记录 M04 部分，成员 C 补充 M05/M06/M07 部分，集成时合并）
- 现象：当时 `docker images` 为空；`docker pull mysql:8.4` 访问 `registry-1.docker.io:443` 超时；本机未安装 MySQL 服务，无法执行 `alembic upgrade head`、`python -m app.db.seed` 和真实接口联调。
- 影响：M04～M07 的真实 migration + seed + DB 端到端联调未执行。
- 处理（2026-10-31）：Docker Desktop 启动后拉取并运行 `mysql:8.4`（Server 8.4.11），在真实库 `club_management` 上执行 `alembic upgrade head`（版本 `20260915_0001`）与 `python -m app.db.seed`。
- 验证（2026-10-31，负责人环境）：
  - 真实数据库共 15 张物理表（14 张业务表 + `alembic_version`），Seed 数据完整。
  - 后端 pytest 全量通过（当前 134 passed，覆盖率 83%）。
  - 冒烟联调 26 项全部通过：四账号真实登录、health 数据库 up、M01 FR-23（列表/403/创建/停用恢复/R03 授予撤销/R02 授予撤销/缺 club_id 400）、M04（草稿→提交→R03 审核→发布→学生报名/取消）、M05（登记经费/汇总）、M06（管理通知/学生收件箱/标记已读）、M07（综合统计/CSV 导出/审计日志）。
  - 成员 A 的 `smoke_m02_m03.py` 在真实库上全部通过（M02/M03 社团与成员流程）。
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
- EI-01、EI-02、EI-03、EI-04、EI-05 已全部解除。
