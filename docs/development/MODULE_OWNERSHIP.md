# Module Ownership V0.1

本文件描述工程模块 ownership，不覆盖此前需求文档 A/B/C 的写作职责。

| Owner | 模块 | 工程职责 | V0.1 状态 |
|---|---|---|---|
| Leader / Integration | M01、公共层 | Engineering Skeleton、身份权限骨架、整体数据模型、API Contract、异常响应、Migration、Seed、集成与 CR | health/auth/me 已实现；FR-23 账号与角色授权 6 个 endpoint + 15 个测试 + AccountsView 管理页面，见 `M01_ACCOUNTS.md` |
| Member A | M02、M03 | 社团注册与年审、成员管理 | 已实现 FR-03～FR-10 及 M07-A 社团/成员统计（Service/Repository/权限/测试/UI），见 `docs/member-a/` |
| Member B | M04 | 活动管理 | 已实现 FR-11～FR-16（Service/状态机/报名/通知/测试/UI），见 `M04_ACTIVITY.md` |
| Member C | M05、M06、M07 | 经费、通知、统计与审计 | 已实现 M05/M06/M07 API、权限、测试和前端，见 `M05_M06_M07_IMPLEMENTATION.md`；真实 MySQL 集成验证已通过（EI-04 已解除） |

## 协作规则

1. 所有人从 `REQUIREMENTS_BASELINE_V1_1.md` 和 `API_CONTRACT_V0_1.md` 开始，不等待其他业务模块先完成。
2. 不私自改变 R/M/FR 编号、路由 method、资源归属或状态名称。
3. M01～M07 已全部实现，不再返回 501；新增或修改 endpoint 时沿用既有响应封装和权限依赖。
4. R02 权限必须检查 `club_role_assignments` 的目标 `club_id`，不得改成全局 `users.role`。
5. R03 不增加学院/部门/辖区过滤；R04 不进入业务审核。
6. 公共响应、异常、认证或数据库结构变更先由 Leader / Integration 审查。
7. 需求矛盾写入 `ENGINEERING_ISSUES_V0_1.md`；需要改需求时标记 `REQUIRES_CR`。

## 代码定位

- M01 / FR-23：`backend/app/api/v1/accounts.py`、`auth.py`；`frontend/src/views/AccountsView.vue`
- M02/M03：`backend/app/api/v1/clubs.py`、`annual_reviews.py`、`members.py`；页面 `ClubsView.vue`、`MembersView.vue`
- M04：`backend/app/api/v1/activities.py`；页面 `ActivitiesView.vue`
- M05/M06/M07：`backend/app/api/v1/finance.py`、`notifications.py`、`reports.py`；页面 `FinanceView.vue`、`NotificationsView.vue`、`ReportsView.vue`
- 领域规则见 `M01_ACCOUNTS.md`、`M04_ACTIVITY.md`、`M05_M06_M07_IMPLEMENTATION.md` 和 `docs/member-a/`
