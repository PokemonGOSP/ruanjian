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

## EI-03：本机 Docker Hub 不可达，M04 真实 MySQL 集成验证待执行

- 类型：环境/网络问题
- 状态：`OPEN`
- 现象：`docker images` 为空；`docker pull mysql:8.4` 访问 `registry-1.docker.io:443` 超时，无法准备 MySQL 8 容器；本机未安装 MySQL 服务。
- 影响：M04 的 Service/状态机/权限/通知由 11 个 pytest 用例覆盖（内存 Repository 替身），SQL 已按 MySQL 方言编译检查；但 migration + seed + 真实 DB 的端到端联调未在本机执行。
- 处理建议：在具备 MySQL 8 或可拉取镜像的环境执行 `docker compose up -d mysql`、`alembic upgrade head`、`python -m app.db.seed`，再按 `docs/development/M04_ACTIVITY.md` 第 7 节复验。
- REQUIRES_CR：否。

## 结论

- 未发现需求层矛盾，不存在 `REQUIRES_CR`。
- EI-01、EI-02 已解除；EI-03 为当前机器 Docker 网络限制，需在具备 MySQL 8 的环境补做 M04 端到端集成验证。
