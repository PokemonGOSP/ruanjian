# 成员 A 工程问题记录

> 说明：现有 `ENGINEERING_ISSUES_V0_1.md` 已有 EI-01、EI-02。本文件使用临时编号 `EI-A-xx`，**不直接修改公共问题记录**；请负责人在合并时分配正式编号或并入公共文件。
> 原则：不静默修改需求；需要改需求/契约的项标记建议，不在本交付中自行实现。

## EI-A-01：M07-A 没有独立 API 契约

- **类型**：契约/分工不一致
- **状态**：`OPEN_FOR_LEADER_DECISION`
- **证据**：
  - `ENGINEERING_SKELETON_V0_1_FINAL.md` 第 3 节把 M07-A（社团/成员统计）分给成员 A；
  - `docs/api/API_CONTRACT_V0_1.md` 第 10 节只定义 `/reports/summary`、`/reports/export`，且 `reports.py` 在骨架中由成员 C 负责；
  - 没有为 M07-A 定义独立 URL 或独立 response schema。
- **本交付处理**：实现只读 Service `club_member_statistics()` + Schema + 测试，**不新增路由**；在 `integration/reports_m07a_snippet.py` 给出 M07 owner 组合方式。
- **需要负责人决定**：
  1. 保持“Service 由 A 提供、路由由 C 组合”（当前方案，零契约变更）；
  2. 若要在 `/reports/summary` 中拆出独立字段，需 C 调整 `ReportSummary` schema；
  3. 若要新增独立 `/reports/club-members` URL，属于 API Contract 变更，需按第 11 节走 CR。
- **影响**：不影响 FR-21 的验收，但合并时需要 A/C 双方确认 `ReportSummary` 字段命名。

## EI-A-02：年审驳回后的重新提交规则未细化

- **类型**：需求细化缺口
- **状态**：`OPEN_FOR_LEADER_DECISION`
- **证据**：
  - `REQUIREMENTS_BASELINE_V1_1.md` 第 4.6 节把“重新提交规则”留给成员 B 在 FR-06/FR-07 中细化；
  - 状态词典写明“已驳回：可复制/修订形成新的提交轮次，是否复用同一申请编号待细化”；
  - 数据库 `annual_review_applications` 有 `(club_id, review_year)` 唯一约束；
  - API Contract 规定 PATCH 只允许“草稿/已撤回可编辑”，`POST /annual-reviews` 重复年度返回 `40902`。
- **本交付处理**：严格按契约实现：`REJECTED` 不可编辑、不可撤回；同年度不能新建第二条。结果是当前被驳回的年度无法在同一自然年重新提交。
- **可选方案**：
  1. **保持现状**：将“驳回即本轮结束”作为课程项目规则；需要重新提交时由负责人决定是否走 CR。
  2. **复用同一条记录**：允许 `REJECTED` 在补充材料后回到 `PENDING`；这会改变状态机的“已驳回不回转”表述，需要 CR。
  3. **新增提交轮次**：给年审增加 `round` 或复制为新记录，并调整唯一约束为 `(club_id, review_year, round)`；需要 Migration 和 CR。
- **建议**：课程原型优先方案 1；若教师明确要求“驳回后可整改重提”，再走 CR 实现方案 3，避免悄悄修改状态语义。
- **影响**：FR-06/FR-07、年审 UI、唯一约束、测试。

## EI-A-03：R03 对 M03 成员申请/名册的访问范围

- **类型**：契约与 CR-04 的表述张力
- **状态**：`OPEN_FOR_LEADER_DECISION`
- **证据**：
  - API Contract 第 6 节：`GET /membership-applications` 为“R01 本人或目标社团 R02”；`GET /clubs/{club_id}/members` 为“目标社团 R02；成员按允许范围”；
  - CR-04 说“所有 R03 默认按既有 FR 对系统内全部社团业务记录执行查看、审核、查询、通知和统计”；
  - FR-08/FR-09/FR-10 的角色列没有 R03。
- **本交付处理**：按 API Contract 的显式角色列实现：R03 不是目标社团 R02、也不是该社团有效成员时，成员申请列表只看到本人申请，名册返回 `40302`。
- **需要负责人决定**：
  1. 保持契约优先（当前实现）；
  2. 若认为 CR-04 覆盖 M03，则把 R03 加入成员申请/名册的只读范围；这需要同步修改 API Contract 第 6 节，并调整测试与前端提示。
- **影响**：FR-08～FR-10 的权限验收、R03 管理视图。

## EI-A-04：M02/M03 直接写通知与审计表

- **类型**：跨模块协作
- **状态**：`COORDINATION_REQUIRED`
- **证据**：
  - FR-19 通知由 M06 负责，FR-22 审计由 M07 负责；
  - 业务事件（注册提交/审核、年审提交/审核、成员申请/处理）必须在事件发生时产生站内通知和关键操作审计；
  - 当前 M06/M07 仍是 Skeleton，没有可调用的 Service。
- **本交付处理**：新增 `app/services/club_member_events.py`，在 M02/M03 业务事务内直接写 `notifications`、`audit_logs`；不修改 M06/M07 的路由或查询逻辑。
- **需要对齐**：
  - `event_type` 命名：`CLUB_REGISTRATION_*`、`ANNUAL_REVIEW_*`、`MEMBERSHIP_APPLICATION_*`；
  - `action` 命名：`CLUB_REGISTRATION_*`、`ANNUAL_REVIEW_*`、`MEMBERSHIP_*`、`CLUB_MEMBER_POSITION_UPDATE`；
  - `related_type`：`club_registration_application`、`annual_review_application`、`membership_application`。
- **建议**：M06/M07 实现后，可把 `club_member_events` 的内部写入替换为调用其 Service，但保持事件名和事务边界不变。
- **影响**：通知列表、审计查询、测试数据。

## EI-A-05：注册通过时为申请人建立负责人成员关系

- **类型**：实现决策
- **状态**：`CONFIRM_WITH_LEADER`
- **证据**：
  - 基线 FR-05 只要求“建立正式社团 + 授予申请人该社团 R02”，没有明确要求同时建立 `ClubMember`；
  - Seed 数据中负责人同时是 `ClubMember(position_name="负责人")`；
  - 若只授予 R02 而不建成员关系，负责人不会出现在 FR-10 名册中，且“负责人退出社团”等场景会缺少成员基线。
- **本交付处理**：审核通过时同时建立申请人 `ClubMember(ACTIVE, position_name="负责人")`，与 Seed 保持一致。
- **需要确认**：这是否符合负责人对“R02 与成员关系独立”的预期。若不需要，删除 `review_registration_application()` 中创建 `ClubMember` 的几行即可，不影响其他逻辑。
- **影响**：FR-05 后置条件、FR-10 名册、成员统计。

## EI-A-06：R01 检查依赖 FR-23 的账号角色初始化

- **类型**：跨模块假设
- **状态**：`COORDINATION_REQUIRED`
- **证据**：M02/M03 的“R01 本人”操作显式检查 `principal.has_system_role("R01")`；当前 Seed 给所有账号授予 R01，但 FR-23 账号创建接口尚未实现。
- **本交付处理**：保留 R01 检查，避免无学生身份的账号发起注册/入团。
- **需要对齐**：FR-23 创建账号时是否默认授予 R01；若 R04 可以创建“纯管理账号”，这些账号不应发起 R01 业务，当前行为正确。
- **影响**：FR-03、FR-08、FR-23。
