# 高校社团活动管理系统——需求数据字典（实验 1 补充件）

> 目的：为冻结基线 V1.1 的 FR-01～FR-23 补足可测试的输入、输出和错误约定。本文件不增加角色、模块或顶层 FR；字段上限是课程验收使用的明确约束，后续如需改变须走 CR。

## 1. 通用表示与响应约定

| 项目 | 约定 |
|---|---|
| 字符串编码 | UTF-8；除密码外，首尾空白在校验前去除。 |
| 时间 | ISO 8601 带时区，例如 `2026-10-19T20:30:00+08:00`。日期为 `YYYY-MM-DD`。 |
| 标识符 | 正整数，范围 `1`～`2147483647`。 |
| 金额 | 十进制定点数 `decimal(12,2)`，不使用二进制浮点；范围 `0.01`～`9999999999.99`。 |
| 成功 JSON | `{ "data": <对象或数组>, "message": "..." }`；删除/退出可为 HTTP 204 无响应体。 |
| 失败 JSON | `{ "error": { "code": "<固定错误码>", "message": "<面向用户的说明>" } }`。 |

### 1.1 固定错误码

| HTTP | 错误码 | 使用条件 |
|---|---|---|
| 400 | `40001` | 字段缺失、类型/范围/枚举错误、时间区间无效或不支持的导出格式。 |
| 401 | `40101` | 缺失、过期或非法 JWT，或用户名/密码不匹配。 |
| 401 | `40104` | 账号已停用，拒绝新登录。 |
| 403 | `40301` | 缺少所需全局系统角色。 |
| 403 | `40302` | 对目标 Club、申请、成员、活动或通知没有资源归属权限。 |
| 404 | `40401` | 指定资源不存在或对调用者不可见。 |
| 409 | `40901` | 重复资源/重复申请/重复报名。 |
| 409 | `40902` | 当前状态不允许该操作或记录已作废。 |

## 2. 认证、账户与授权（FR-01、FR-02、FR-23）

| 数据对象 | 字段（类型；必填；约束） | 输出关键字段 |
|---|---|---|
| `LoginInput` | `username`（string；是；1～64）；`password`（string；是；1～128） | `access_token`（string）；`token_type` 固定 `bearer`；`user.id`、`user.username`、`user.status`。 |
| `AccountInput` | `username`（string；是；1～64，唯一）；`display_name`（string；是；1～80）；`status`（enum；是；`ACTIVE`/`DISABLED`） | `id`、上述字段、`created_at`、`updated_at`。密码仅以写入字段出现，任何输出不得包含密码或密码哈希。 |
| `RoleAssignmentInput` | `user_id`（integer；是）；`role_code`（enum；是；`R02`/`R03`/`R04`）；`club_id`（integer；R02 必填，R03/R04 必须为空） | `user_id`、`role_code`、`club_id`（R02 必返回具体 Club）、`assigned_at`。 |
| `AuthMeOutput` | 无额外输入 | `id`、`username`、`display_name`、`status`、系统角色列表、R02 的 `club_ids` 列表。 |

R01 是默认登录学生身份；R02 是“用户—具体 Club”授权记录，不能作为全局 `users.role`。R03、R04 是系统级角色，职责仍以 V1.1 基线为准。

## 3. 社团注册、社团资料与年审（FR-03～FR-07）

| 数据对象 | 字段（类型；必填；约束） | 输出关键字段 |
|---|---|---|
| `ClubRegistrationInput` | `proposed_name`（string；是；1～150）；`description`（string；是；1～5000）；`contact_name`（string；是；1～80）；`contact_phone`（string；是；7～32）；`advisor_contact`（string；否；1～255） | `id`、`applicant_user_id`、输入字段、`status`、`submitted_at`、`review_comment`。 |
| `ReviewInput` | `decision`（enum；是；`APPROVE`/`REJECT`）；`comment`（string；通过时否、最多 1000；驳回时必填且 1～1000） | `status`（“已通过”或“已驳回”）、`reviewer_user_id`、`reviewed_at`、`review_comment`。 |
| `ClubProfileInput` | `name`（string；是；1～150）；`description`（string；是；1～5000）；`contact_name`（string；是；1～80）；`contact_phone`（string；是；7～32）；`advisor_contact`（string；否；1～255） | `club.id`、上述资料、`status`。指导教师仅为可选联系人，不表示系统角色或审核权。 |
| `AnnualReviewInput` | `club_id`（integer；是）；`review_year`（integer；是；2000～2100）；`material_text`（string；是；1～5000） | `id`、`club_id`、`review_year`、`status`、`submitted_by`、`submitted_at`、审核字段。 |

申请状态仅使用“草稿、待审核、已通过、已驳回、已撤回”。注册申请只能由申请人 R01 在“待审核”撤回；年审申请只能由有该 Club 权限的 R02 在“待审核”撤回；已通过和已驳回不能撤回。

## 4. 成员与活动（FR-08～FR-16）

| 数据对象 | 字段（类型；必填；约束） | 输出关键字段 |
|---|---|---|
| `MembershipApplicationInput` | `club_id`（integer；是）；`application_type`（enum；是；`JOIN`/`LEAVE`）；`reason`（string；否；最多 1000） | `id`、`club_id`、`applicant_user_id`、`application_type`、`status`、时间与处理意见。 |
| `MemberRoleInput` | `member_user_id`（integer；是）；`position`（string；否；1～80） | `club_id`、`member_user_id`、`membership_status`、`position`、`effective_at`、`ended_at`。 |
| `ActivityCreateInput` | `club_id`（integer；是）；`title`（string；是；1～200）；`description`（string；是；1～5000）；`location`（string；是；1～255）；`starts_at`（datetime；是）；`ends_at`（datetime；是，且晚于开始）；`registration_deadline`（datetime；否，早于开始）；`capacity`（integer；否；1～10000）；`budget_amount`（decimal(12,2)；否；0～9999999999.99） | `id`、全部业务字段、`review_status`、`execution_status`、`created_by`、时间戳。 |
| `ActivitySubmitOrWithdrawInput` | `action`（enum；是；`SUBMIT`/`WITHDRAW`） | `review_status`。只有授权 R02 能操作本 Club；撤回仅限其本 Club 提交且“待审核”的申请。 |
| `ActivityReviewInput` | 使用 `ReviewInput` | `review_status`、审核意见与时间。 |
| `ActivityPublishInput` | `action`（固定 `PUBLISH`） | 当报名窗口开放时，`execution_status` 由“未发布”变为“报名中”；“已发布”不是状态值。 |
| `ActivityRegistrationInput` | `activity_id`（integer；是） | `id`、`activity_id`、`student_user_id`、`status`（`REGISTERED`/`CANCELLED`）、`created_at`。 |
| `ActivityExecutionInput` | `action`（enum；是；`CANCEL`/`FINISH`/`ARCHIVE`）；`reason`（string；取消时必填 1～1000，其他可空） | `CANCEL` 后执行状态为“已取消”；`FINISH` 后为“已结束”；`ARCHIVE` 仅为已结束活动写入 `archived_at`，不产生“已归档”执行状态。 |

活动审核状态和执行状态分离。执行状态仅使用“未发布、报名中、报名截止、进行中、已结束、已取消”。报名只对“报名中”、未到报名截止、且未满员的活动开放；没有活动签到字段或接口。

## 5. 经费、通知、统计与审计（FR-17～FR-22）

| 数据对象 | 字段（类型；必填；约束） | 输出关键字段 |
|---|---|---|
| `FinanceRecordInput` | `club_id`（integer；是）；`activity_id`（integer；否，若给出必须属于该 Club）；`record_type`（enum；是；`INCOME`/`EXPENSE`）；`amount`（decimal(12,2)；是；0.01～9999999999.99）；`occurred_on`（date；是）；`description`（string；是；1～500）；`voucher_reference`（string；否；1～255）；`attachments`（对象数组；否；0～5 个） | `id`、上述字段、`record_status`（`VALID`/`VOIDED`）、`created_by`、`voided_at`、`void_reason`。不包含支付、报销审核或实际财务结算字段。 |
| `FinanceQuery` | `club_id`（integer；否，取值须在可见范围）；`activity_id`（integer；否）；`record_type`（enum；否）；`date_from/date_to`（date；否，若均有则 from≤to） | `items`、`income_total`、`expense_total`、`net_total`；作废记录不计入汇总。 |
| `BusinessNotificationOutput` | 由业务事件产生，无用户自定义外部渠道输入 | `id`、`recipient_user_id`、`title`、`content`、`is_read`、`created_at`、`read_at`。 |
| `ManagementNotificationInput` | `target_type`（enum；是；`USER`/`ROLE`/`CLUB`）；`target_ids`（integer 数组；是；1～1000 个且每个为正数）；`title`（string；是；1～200）；`content`（string；是；1～5000） | 每个目标的站内通知记录。当前不输出邮件、短信、企业微信或校内消息平台调用。 |
| `ReportQuery` | `dimension`（enum；是；`CLUB`/`MEMBER`/`ACTIVITY`/`REGISTRATION`/`FINANCE`）；`club_id/activity_id`（integer；否）；`date_from/date_to`（date；否，from≤to）；`format`（enum；否；`JSON`/`CSV`，缺省 `JSON`） | JSON 为 `summary` 与 `items`；CSV 固定 UTF-8、逗号分隔、首行字段名，HTTP `Content-Type: text/csv; charset=utf-8`。不支持 XLSX/PDF。 |
| `AuditLogOutput` | 查询过滤：`actor_user_id`、`operation_type`、`date_from/date_to`（均可选，日期范围合法） | `id`、`actor_user_id`、`operation_type`、`target_type`、`target_id`、`result`、`occurred_at`。普通用户没有删除或修改入口。 |

`attachments` 中每项为 `AttachmentMetadataInput`：`file_name`（string；是；1～255）、`content_type`（enum；是；`application/pdf`、`image/jpeg`、`image/png`）、`size_bytes`（integer；是；1～10,485,760）、`storage_ref`（string；是；1～255）。任一项超出类型、大小或数量限制返回 `40001`；课程原型可只保存元数据或本地模拟引用，不要求第三方文件存储、发票验真或财务审核。

## 6. 字段与页面/接口的一致性原则

- 表单显示的必填、长度、枚举和时间限制必须与本字典一致；后端不得仅依赖前端校验。
- 查询输出仅可包含调用者在 FR-02 授权范围内的字段和记录。
- 枚举显示文案可中文化，但持久化/API 值使用本字典的固定代码；状态展示仍使用 V1.1 的固定中文状态词。
- 任何新增字段、导出格式、错误码或外部集成均不是本次补充件授权范围，须先记录 CR。

## 7. 个人信息最小化与展示规则（CR-07）

| 数据类别 | 当前可收集字段 | 可见范围 | 导出与保留约束 |
|---|---|---|---|
| 账号基本信息 | `username`、`display_name`、账号状态 | 本人；R04 仅为账号管理读取必要字段 | 默认统计/CSV 不导出；课程验收结束或测试库重置后 30 天内删除或不可逆匿名化。 |
| 社团联系人 | `contact_name`、`contact_phone`、可选 `advisor_contact` | 注册申请由申请人本人和 R03 查看；获准社团资料由对应 Club 的 R02 和 R03 查看 | 默认统计/CSV 不导出；不作为活动公开详情字段。 |
| 审计信息 | `actor_user_id`、操作类型、对象、结果、时间 | R04；R03 仅按既有 FR 的业务查询范围读取 | 不记录密码、JWT、完整联系电话或附件二进制内容。 |

当前课程原型不收集学号、身份证号、支付账户、精确位置或生物特征。若后续需要收集或导出任何上述信息，必须先通过 CR 定义用途、角色范围、保留期限和验收方法。
