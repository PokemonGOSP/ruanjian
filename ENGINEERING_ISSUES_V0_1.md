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

## EI-03：请求参数校验错误响应无法序列化

- 类型：公共异常处理缺陷
- 状态：`RESOLVED`
- 现象：`RequestValidationError.errors()` 的 `ctx` 中可能包含 `ValueError` 或 `Decimal`，原 `JSONResponse` 直接序列化时抛 `TypeError`，导致本应返回 422/40001 的请求变成 500。
- 触发场景：成员 C 的经费金额校验（如 `amount=0`）、自定义 Pydantic validator 失败时。
- 处理：在 `app/core/exceptions.py` 中移除不可序列化的 `ctx`，并使用 `jsonable_encoder` 编码错误数据；响应结构仍为 `{code,message,data}`，错误码不变。
- 影响：所有模块的参数校验错误响应；建议负责人按公共异常处理变更规则复核。
- REQUIRES_CR：否。

## EI-04：当前环境缺少 MySQL，成员 C 集成验证未执行

- 类型：环境缺失
- 状态：`OPEN`
- 现象：当前 Windows 环境没有 Docker 和 MySQL 客户端/服务，无法执行 `alembic upgrade head`、`python -m app.db.seed` 和真实接口集成验证。
- 已执行：成员 C 与既有单元/接口测试 27 项通过；完整 `pytest` 为 `27 passed, 1 failed`，唯一失败为 `tests/test_health.py` 需要真实 MySQL。OpenAPI 生成和前端构建通过。
- 处理：不得用 SQLite 替代 MySQL；需在具备 MySQL 8 的负责人/WSL 环境补测，并记录到验证文档。
- REQUIRES_CR：否。

## 结论

- 未发现需求层矛盾，不存在 `REQUIRES_CR`。
- EI-03 已修复；EI-04 需在具备 MySQL 的环境补测后关闭。
- 当前工程阻塞已解除。
