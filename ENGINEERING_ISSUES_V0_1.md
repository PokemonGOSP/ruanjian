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
- 状态：`BLOCKED`
- 发现时间：2026-10-26
- 现象：当前 Windows Python 3.12 与 WSL Python 3.12 均未安装 `pytest`、`ruff` 及项目运行依赖；按现有 `backend/requirements.txt` 启动安装时仅完成部分下载元数据，未形成可用环境。
- 影响范围：`feature/m01-auth` 当前已完成的 R04 账号列表、创建本地测试账号、账号资料/状态更新、角色授权授予四个竖切片均已编写代码与测试用例，但完整 `pytest` 和 `ruff` 尚未实际执行，不能标记为 PASS。
- 已完成检查：Python 语法编译（无第三方导入）与 `git diff --check` 均通过。
- 后续处理：恢复一个可用的、由 `backend/requirements.txt` 构建的 Python 环境后，优先执行 `pytest tests/test_accounts.py -q`、完整 `pytest` 与 `ruff check`；验证结果需追加到工程验证记录。
- REQUIRES_CR：否。该问题不改变角色、FR、接口语义或数据模型。

## 结论

- 未发现需求层矛盾，不存在 `REQUIRES_CR`。
- Engineering Skeleton V0.1 的既有 MySQL 阻塞已解除；EI-03 使当前 M01 增量的自动化验证暂时未完成。
