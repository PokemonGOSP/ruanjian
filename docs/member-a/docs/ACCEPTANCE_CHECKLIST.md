# 成员 A 验收对照清单

> 对应 FR-03～FR-10，以及 FR-21 中社团/成员统计部分。
> 自动化测试见 `TEST_REPORT.md`；手工步骤使用 Seed 账号，数据均为虚构。
> **2026-10-30 已执行真实 MySQL 8.4.11 + Chrome 156 浏览器验收，9 步主流程全部通过；截图与证据见 [`REAL_DB_AND_BROWSER_ACCEPTANCE.md`](REAL_DB_AND_BROWSER_ACCEPTANCE.md)。**

## 0. 测试账号

| 账号 | 密码 | 身份 |
|---|---|---|
| `student01` | `Student123!` | R01，星河读书社成员 |
| `student02` | `Student123!` | R01，无社团负责人授权 |
| `leader01` | `Leader123!` | R01 + Club 1/3 的 R02 |
| `manager01` | `Manager123!` | R01 + R03 |
| `admin01` | `Admin123!` | R01 + R04（本模块不用于业务审核） |

## 1. 验收对照

| 验收编号 | FR | 验收目标 | 自动化覆盖 | 手工步骤 | 通过条件 |
|---|---|---|---|---|---|
| AC-FR-03-01 | FR-03 | R01 创建草稿并提交注册申请 | `test_create_registration_starts_as_draft`、`test_submit_and_withdraw_registration_follow_state_machine` | student01 → 社团/年审 → 新建 → 保存 → 提交 | 状态从草稿变待审核；列表出现记录 |
| AC-FR-03-02 | FR-03 | 非本人不能编辑/提交/撤回 | `test_update_registration_only_owner_in_editable_status` | 用 student02 调同一申请 ID 的 PATCH/submit/withdraw | 返回 40301，数据不变 |
| AC-FR-03-03 | FR-03 | 待审核可撤回，撤回后可再提交 | `test_submit_and_withdraw_registration_follow_state_machine` | 提交 → 撤回 → 编辑 → 再提交 | 状态 `PENDING → WITHDRAWN → PENDING` |
| AC-FR-04-01 | FR-04 | 登录用户查询社团列表/详情 | `test_club_list_route_returns_page_data`、`test_update_club_requires_target_club_r02` | 任意账号打开社团资料 | 返回已建立社团；分页字段正确 |
| AC-FR-04-02 | FR-04 | 只有目标社团 R02 可修改资料 | `test_update_club_requires_target_club_r02` | leader01 改 Club 1 成功；student02 改同一社团失败 | 成功 200；失败 40302 |
| AC-FR-04-03 | FR-04 | 社团名称唯一 | 无独立自动化（合并后手工验证） | leader01 把 Club 1 改成 Club 2 的名称 | 返回 40902，名称不变 |
| AC-FR-05-01 | FR-05 | R03 通过注册申请并建立 Club + 该社团 R02 | `test_review_registration_approves_and_grants_club_scoped_r02`、`smoke_m02_m03.py` | manager01 审核 student02 的待审核申请 → 通过 | 返回 `club` 与 `club_authorization`（`club_id` 对应新社团）；申请人 `/auth/me` 出现该社团 R02 |
| AC-FR-05-02 | FR-05 | 驳回必须填理由，且不建立 Club/不授权 | `test_review_registration_rejection_creates_no_club`、`test_review_registration_rejection_requires_reason` | manager01 驳回且不填理由 → 失败；填写理由 → 成功 | 失败 40001；成功后无新 Club，申请人无新 R02 |
| AC-FR-05-03 | FR-05 | 申请人与审核人不能相同 | `test_review_registration_blocks_applicant_as_reviewer` | 给同一账号同时加 R03 后审核自己的申请 | 返回 40301 |
| AC-FR-06-01 | FR-06 | R02 创建/提交年审草稿 | `test_create_annual_review_starts_as_draft`、`test_submit_and_withdraw_annual_review` | leader01 → 年审 → 新建 → 提交 | 状态 `DRAFT → PENDING`；列表可见 |
| AC-FR-06-02 | FR-06 | 同社团同年度不能重复 | `test_create_annual_review_rejects_duplicate_year` | 对同一社团/年度再次新建 | 返回 40902 |
| AC-FR-06-03 | FR-06 | 非本社团 R02 不能创建/提交/撤回 | `test_create_annual_review_requires_target_club_r02` | student02 对 Club 1 创建年审 | 返回 40302 |
| AC-FR-07-01 | FR-07 | R03 审核年审并保存意见 | `test_review_annual_review_saves_result_without_freezing_club` | manager01 审核待审核年审 | 状态/意见/审核人/时间正确 |
| AC-FR-07-02 | FR-07 | 驳回不冻结社团、不影响其他业务 | `test_review_annual_review_saves_result_without_freezing_club` | 驳回后 leader01 仍可改社团资料、提交活动/经费（M04/M05 就绪时） | Club/账号/其他权限未被自动修改；仅年审状态与通知变化 |
| AC-FR-07-03 | FR-07 | 驳回必须填写意见 | `test_review_annual_review_rejection_requires_comment` | 驳回时留空意见 | 返回 40001，状态仍 `PENDING` |
| AC-FR-08-01 | FR-08 | 有效成员不能重复入团 | `test_create_join_application_rejects_active_member` | student01 对 Club 1 申请入团 | 返回 40002 |
| AC-FR-08-02 | FR-08 | 非成员不能申请退出 | `test_create_exit_application_requires_active_member` | student02 对 Club 1 申请退出 | 返回 40002 |
| AC-FR-08-03 | FR-08 | 待处理申请不可重复提交 | `test_create_join_application_rejects_duplicate_pending` | 同一用户对同一社团连续提交两次 | 第二次 40902 |
| AC-FR-08-04 | FR-08 | 待处理申请可由本人撤回 | `test_withdraw_membership_application_only_pending` | student01 提交后撤回 | 状态 `PENDING → WITHDRAWN` |
| AC-FR-09-01 | FR-09 | R02 同意入团后建立有效成员关系 | `test_process_join_application_creates_member`、`smoke_m02_m03.py` | leader01 处理 student02 的入团申请 → 同意 | `ClubMember.status=ACTIVE`；名册出现该成员 |
| AC-FR-09-02 | FR-09 | R02 同意退出后成员关系变已退出 | `test_process_exit_application_marks_member_exited` | 对有效成员提交退出 → 同意 | `status=EXITED`，`exited_at` 非空 |
| AC-FR-09-03 | FR-09 | 驳回不改成员关系 | `test_process_application_rejection_keeps_membership_unchanged` | 处理入团 → 驳回 | 申请 `REJECTED`；成员关系不变 |
| AC-FR-09-04 | FR-09 | 非本社团 R02 不能处理；不能处理本人申请 | `test_process_application_blocks_same_person`、服务权限检查 | student02 处理 Club 1 申请；或 R02 处理自己的申请 | 40302 / 40301 |
| AC-FR-10-01 | FR-10 | 负责人查看完整名册 | `test_member_roster_full_for_leader_and_limited_for_member` | leader01 打开成员名册 | 可见账号、姓名、职务、加入/退出时间 |
| AC-FR-10-02 | FR-10 | 有效成员只看本人记录与受限字段 | `test_member_roster_full_for_leader_and_limited_for_member` | student01（Club 1 成员）打开 Club 1 名册 | 只出现本人记录；`user_id/username/joined_at/exited_at` 为 null |
| AC-FR-10-03 | FR-10 | 非成员不能看名册 | `test_member_roster_full_for_leader_and_limited_for_member` | student02 打开 Club 1 名册 | 40302 |
| AC-FR-10-04 | FR-10 | R02 维护有效成员职务 | `test_update_member_position_requires_leader_and_active_member` | leader01 给成员设置/清空职务 | 成功；已退出成员返回 40901 |
| AC-FR-21-01 | FR-21 | 社团/成员统计按权限返回 | `test_statistics_r02_scopes_to_own_clubs`、`test_statistics_r03_sees_all_clubs` | 由 M07 `/reports/summary` 组合后查看 | R02 只见负责社团；R03 见全部；R01 403 |

## 2. 手工复验顺序（自动化验收已执行）

1. **注册主链**
   - student02 登录 → 社团/年审 → 新建“成员A手工社团” → 提交。
   - manager01 登录 → 社团/年审 → 审核 → 通过。
   - student02 点“刷新身份与授权” → 首页“负责社团”出现新社团。
2. **R02 资料与年审**
   - student02 → 社团资料 → 编辑简介 → 保存。
   - 年审 → 新建（选择新社团，年度 2099）→ 提交。
   - manager01 → 年审 → 驳回，填意见；确认新社团仍可编辑资料、仍可处理成员。
3. **成员主链**
   - student01 → 成员 → 提交申请（选择新社团，JOIN）→ 提交。
   - student02 → 成员 → 范围“我负责社团的申请” → 处理 → 同意。
   - student02 → 成员名册 → 选择新社团 → 看到 student01；维护职务为“成员”。
   - student01 → 成员名册 → 选择新社团 → 只看到本人的受限记录。
4. **越权**
   - leader01 尝试编辑 student02 新社团资料 → 应失败。
   - student02 尝试审核注册申请（无 R03）→ 前端不显示审核按钮；直接调 API 返回 40301。
   - student02 尝试处理自己的成员申请 → 返回 40301。

## 3. 记录要求

- 手工验收时保存页面截图、请求/响应或日志，作为课程报告的“用户反馈/测试”材料。
- 不要把 Seed 的虚构数据描述为真实学校数据。
- 若发现不符合基线的情况，先记录 EI/CR，不要直接修改需求或状态名称。
