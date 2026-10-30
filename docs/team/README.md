# 团队开发统一入口

队友开始开发前，按以下顺序阅读。本文档只提供入口，不复制或移动正式基线文件；正式文件仍保留原路径，避免引用失效。

## 1. 全员必读

1. [`REQUIREMENTS_BASELINE_V1_1.md`](../../REQUIREMENTS_BASELINE_V1_1.md)：正式需求基线，角色、模块、FR、状态和边界的唯一依据。
2. [`ENGINEERING_SKELETON_V0_1_FINAL.md`](../../ENGINEERING_SKELETON_V0_1_FINAL.md)：V0.1 工程封装、并行开发原则和集成规则。
3. [`ENGINEERING_VALIDATION_V0_1.md`](../../ENGINEERING_VALIDATION_V0_1.md)：MySQL、Migration、Seed、认证链和前端构建验证结果。
4. [`README.md`](../../README.md)：环境安装、启动、Migration、Seed、测试和构建命令。

## 2. 按角色阅读

### 项目负责人 / Integration

- [`docs/development/MODULE_OWNERSHIP.md`](../development/MODULE_OWNERSHIP.md)
- [`docs/architecture/ENGINEERING_BASELINE_V0_1.md`](../architecture/ENGINEERING_BASELINE_V0_1.md)
- [`docs/api/API_CONTRACT_V0_1.md`](../api/API_CONTRACT_V0_1.md)
- [`docs/api/ERROR_CODES.md`](../api/ERROR_CODES.md)
- [`CHANGE_REQUESTS_ROUND3.md`](../../CHANGE_REQUESTS_ROUND3.md)

负责 M01、公共模型与权限、Migration、Seed、公共 API 约定、集成和 CR。

### 成员 A

- [`docs/development/MODULE_OWNERSHIP.md`](../development/MODULE_OWNERSHIP.md)
- [`docs/api/API_CONTRACT_V0_1.md`](../api/API_CONTRACT_V0_1.md) 中 M02、M03 部分
- [`REQUIREMENTS_BASELINE_V1_1.md`](../../REQUIREMENTS_BASELINE_V1_1.md) 中 FR-03～FR-10

负责 M02、M03，以及 M07-A 社团/成员统计。

### 成员 B

- [`docs/development/MODULE_OWNERSHIP.md`](../development/MODULE_OWNERSHIP.md)
- [`docs/api/API_CONTRACT_V0_1.md`](../api/API_CONTRACT_V0_1.md) 中 M04 部分
- [`REQUIREMENTS_BASELINE_V1_1.md`](../../REQUIREMENTS_BASELINE_V1_1.md) 中 FR-11～FR-16

负责 M04，以及 M07-B 活动/报名统计。

### 成员 C

- [`docs/development/MODULE_OWNERSHIP.md`](../development/MODULE_OWNERSHIP.md)
- [`docs/api/API_CONTRACT_V0_1.md`](../api/API_CONTRACT_V0_1.md) 中 M05、M06、M07 部分
- [`REQUIREMENTS_BASELINE_V1_1.md`](../../REQUIREMENTS_BASELINE_V1_1.md) 中 FR-17～FR-23

负责 M05、M06，以及 M07-C 经费、审计和综合统计。

## 3. 开发前必须确认

- 不修改需求基线；需求变化记录 `CR-xx`。
- 工程问题记录 `EI-xx`；不得用 SQLite 等替代 MySQL。
- 不把 R02 实现为全局用户角色；必须保留用户—具体 Club 授权关系。
- 不实现范围外的 SSO、支付、签到、多级审批、外部通知等功能。
- M02～M07 当前是 Skeleton；每项实现必须同时覆盖 API、数据库、权限、测试和文档。

## 4. Git 分支规则

- 禁止直接在 `main` 上开发业务功能。
- `main` 只接收已经验证、准备集成的代码。
- 负责人使用 `feature/m01-auth`；成员 A 使用 `feature/m02-m03-club-member`；成员 B 使用 `feature/m04-activity`；成员 C 使用 `feature/m05-m06-m07-ops`。
- 开发、测试和提交均在各自 `feature/...` 分支完成，验证通过后再合并到 `main`。
- 不使用 `git push --force`；合并前必须确认工作区干净、测试通过且没有未处理的 `CR/EI`。

## 5. 常用命令

```powershell
docker compose up -d mysql
cd backend
alembic upgrade head
python -m app.db.seed
pytest
cd ..\frontend
npm.cmd install
npm.cmd run build
```

详细命令和环境差异以根目录 `README.md` 为准。
