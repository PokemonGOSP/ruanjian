# Module Ownership V0.1

本文件描述工程模块 ownership，不覆盖此前需求文档 A/B/C 的写作职责。

| Owner | 模块 | 工程职责 | V0.1 状态 |
|---|---|---|---|
| Leader / Integration | M01、公共层 | Engineering Skeleton、身份权限骨架、整体数据模型、API Contract、异常响应、Migration、Seed、集成与 CR | health/auth/me 已实现；FR-23 路由 skeleton |
| Member A | M02、M03 | 社团注册与年审、成员管理 | `TODO(Member A)`；契约和路由 skeleton 已预留 |
| Member B | M04 | 活动管理 | 已实现 FR-11～FR-16（Service/状态机/报名/通知/测试/UI），见 `M04_ACTIVITY.md` |
| Member C | M05、M06、M07 | 经费、通知、统计与审计 | `TODO(Member C)`；契约和路由 skeleton 已预留 |

## 协作规则

1. 所有人从 `REQUIREMENTS_BASELINE_V1_1.md` 和 `API_CONTRACT_V0_1.md` 开始，不等待其他业务模块先完成。
2. 不私自改变 R/M/FR 编号、路由 method、资源归属或状态名称。
3. M02～M07 的 skeleton 返回 501 是有意设计；owner 在实现时替换对应 handler 和 `PayloadRequest`。
4. R02 权限必须检查 `club_role_assignments` 的目标 `club_id`，不得改成全局 `users.role`。
5. R03 不增加学院/部门/辖区过滤；R04 不进入业务审核。
6. 公共响应、异常、认证或数据库结构变更先由 Leader / Integration 审查。
7. 需求矛盾写入 `ENGINEERING_ISSUES_V0_1.md`；需要改需求时标记 `REQUIRES_CR`。

## TODO 定位

- `backend/app/api/v1/clubs.py`、`annual_reviews.py`、`members.py`：TODO(Member A)
- `backend/app/api/v1/activities.py`：TODO(Member B)
- `backend/app/api/v1/finance.py`、`notifications.py`、`reports.py`：TODO(Member C)
- `frontend/src/views/*View.vue`：对应模块的最小占位页
