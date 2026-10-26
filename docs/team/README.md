# 团队开发统一入口

队友开始开发前，按以下顺序阅读。本文档只提供入口，不复制或移动正式基线文件；正式文件仍保留原路径，避免引用失效。

## 1. 全员必读

1. [`REQUIREMENTS_BASELINE_V1_1.md`](../../REQUIREMENTS_BASELINE_V1_1.md)：正式需求基线，角色、模块、FR、状态和边界的唯一依据。
2. [`ENGINEERING_SKELETON_V0_1_FINAL.md`](../../ENGINEERING_SKELETON_V0_1_FINAL.md)：V0.1 工程封装、并行开发原则和集成规则。
3. [`ENGINEERING_VALIDATION_V0_1.md`](../../ENGINEERING_VALIDATION_V0_1.md)：MySQL、Migration、Seed、认证链和前端构建验证结果。
4. [`README.md`](../../README.md)：环境安装、启动、Migration、Seed、测试和构建命令。

## 1.1 课程实验提交材料

- [`REQUIREMENTS_ANALYSIS_FINAL.md`](../../REQUIREMENTS_ANALYSIS_FINAL.md)：展开后的需求分析正文。
- [`REQUIREMENTS_TRACEABILITY.md`](../../REQUIREMENTS_TRACEABILITY.md)：需求来源、FR、验收和变更追踪矩阵。
- [`AI_COLLABORATION_RECORD.md`](../../AI_COLLABORATION_RECORD.md)：Round 1～3 AI 协作汇总记录。
- [`MANUAL_VERIFICATION_NOTES.md`](../../MANUAL_VERIFICATION_NOTES.md)：人工确认、核实边界和待核实事项。
- [`CHANGE_REQUESTS_ROUND3.md`](../../CHANGE_REQUESTS_ROUND3.md)：CR-01～CR-05 变更记录。

## 1.2 设计阶段提交材料

- [`DESIGN_DOCUMENT_V0_1.md`](../../DESIGN_DOCUMENT_V0_1.md)：架构、模块、接口、数据、流程、界面、非功能、异常、权衡和测试设计。
- [`DESIGN_REQUIREMENTS_BASELINE.md`](../../DESIGN_REQUIREMENTS_BASELINE.md)：设计文档与实验 1 需求基线的编号对照。
- [`DESIGN_CHANGE_NOTES_V0_1.md`](../../DESIGN_CHANGE_NOTES_V0_1.md)：设计阶段需求变更说明；当前结论为无新需求变更。

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

## 4.1 AI 协作、人工修改与证据规则

- AI 只能提供建议、草稿、检查或测试辅助；需求、架构、权限、状态、接口语义和范围的最终决定必须由负责人确认。
- 对每个实质性人工修改保留可追溯记录：原问题/AI 建议或旧文本 → 人工决定后的文本 → 修改、采纳或否决理由 → 受影响的 R/M/FR/API/数据/测试 → 核实状态。
- 需求含义、角色、模块、FR、状态、术语、边界或优先级的变化必须记录 `CR-xx`；工程实现问题、环境问题和已知限制记录 `EI-xx`。未经批准不得静默改基线。
- 不得伪造用户访谈、教师意见、学校规章、真实系统接口、压测结果或人工核实。未获得证据的现实事项必须标“待核实”。
- 代码与文档必须使用同一编号、状态词和错误码；错误码以 `docs/api/ERROR_CODES.md` 为唯一来源。

## 4.2 小步提交与同步规则

- 每完成一个**可验证的小部分**就在本人 `feature/...` 分支创建一次提交并推送 GitHub。例如：一个领域 Schema、一个 API 垂直切片、一个数据库迁移、一个状态机、对应测试，或一次受控文档修订。
- 一个提交只解决一个连贯目标；禁止为增加次数创建空提交、纯格式噪声提交或未经验证的大杂烩提交。
- 提交前至少执行与改动相称的检查：文档执行 `git diff --check`；后端执行相关 pytest/迁移检查；前端执行对应测试或 build。提交信息说明“做了什么”，必要时写 FR/CR/EI 编号。
- 推送后在 PR 或任务记录中说明：验证命令与结果、已知限制、是否存在 `REQUIRES_CR`/`EI`。未完成或未验证的事项必须明确标为 NOT RUN/BLOCKED，不能写 PASS。
- 禁止直接在 `main` 开发；负责人仅在功能分支通过审查、验证和冲突处理后合并到 `main`。

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
