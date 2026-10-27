# API Contract V0.1

## 1. 通用约定

- Base URL：`/api/v1`
- 认证：`Authorization: Bearer <JWT>`；除 login 和 health 外均需登录。
- 成功：`{"code":0,"message":"success","data":...}`。
- 失败：`{"code":<error_code>,"message":"具体原因","data":null}`。
- 分页：`page` 从 1 开始，`page_size` 为 1～100；响应 `data={items,page,page_size,total}`。
- R02 是目标 `club_id` 的资源级授权，不是全局角色；R03 可按既有 FR 访问系统内全部社团业务记录；R04 不参与业务审核。
- `PayloadRequest` 是 V0.1 占位 schema，成员实现时必须在不改变路径语义的前提下替换为领域 schema。
- Skeleton 路由统一返回 HTTP 501 / code 50101；已实现路由见表中 `implemented`。

主要响应 schema：`TokenData`、`CurrentUserData`、`PageData<T>`、`Resource`（对应领域资源）、`EmptyObject`。主要请求 schema：`LoginRequest`、`AccountCreateRequest`、`AccountUpdateRequest`、`RoleAssignmentRequest`、`ReviewRequest`、`ReasonRequest`、`ActivityCreateRequest`、`FinanceRecordCreateRequest`、`FinanceRecordUpdateRequest`、`ManagementNotificationRequest`。

## 2. Health 与认证

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| GET | `/health` | 工程基础 | 公开 | 无 | `{service,database}` | 无 | 50000 | implemented |
| POST | `/auth/login` | FR-01 | 公开；账号须正常 | LoginRequest | TokenData | 正常账号 | 40001,40104 | implemented |
| POST | `/auth/logout` | FR-01 | 当前用户 | 无 | EmptyObject | JWT 有效 | 40101,40102 | implemented |
| GET | `/auth/me` | FR-01, FR-02 | 当前用户 | 无 | CurrentUserData（系统角色与 R02 社团摘要） | JWT 有效且账号正常 | 40101～40103 | implemented |

FR-02 是所有受保护 endpoint 的横切权限需求：后续实现必须同时检查系统角色、账号状态和资源归属。

## 3. Accounts（M01）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| GET | `/accounts` | FR-23 | R04 | page,page_size | PageData<Account> | 无 | 40101,40301 | skeleton |
| POST | `/accounts` | FR-23 | R04 | AccountCreateRequest | Account | 用户名唯一 | 40001,40301,40902 | skeleton |
| PATCH | `/accounts/{account_id}` | FR-23 | R04 | AccountUpdateRequest | Account | 账号存在 | 40301,40401,40901 | skeleton |
| POST | `/accounts/{account_id}/role-assignments` | FR-23 | R04；R02 必须带 club_id | RoleAssignmentRequest | RoleAssignment | 账号/社团存在 | 40002,40301,40401,40902 | skeleton |
| DELETE | `/accounts/{account_id}/role-assignments/{role_code}` | FR-23 | R04；仅 R03/R04 系统授权 | 无 | EmptyObject | 授权有效 | 40301,40401,40901 | skeleton |
| DELETE | `/accounts/{account_id}/club-role-assignments/{club_id}` | FR-23 | R04；目标社团 R02 授权 | 无 | EmptyObject | 授权有效 | 40301,40401,40901 | skeleton |

账号停用或授权撤销不得删除历史业务数据；所有授权变更应产生审计记录。

## 4. Clubs（M02）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| POST | `/club-registration-applications` | FR-03 | R01 本人 | PayloadRequest | ClubRegistrationApplication | 新建为草稿 | 40001,40101 | skeleton |
| GET | `/club-registration-applications` | FR-03,FR-05 | R01 本人或 R03 全部 | page,page_size | PageData<Application> | 无 | 40301 | skeleton |
| PATCH | `/club-registration-applications/{application_id}` | FR-03 | R01 申请本人 | PayloadRequest | Application | 草稿/已撤回可编辑 | 40301,40401,40901 | skeleton |
| POST | `/club-registration-applications/{application_id}/submit` | FR-03 | R01 申请本人 | 无 | Application | 草稿/已撤回 → 待审核 | 40301,40901 | skeleton |
| POST | `/club-registration-applications/{application_id}/withdraw` | FR-03 | R01 申请本人 | 无 | Application | 待审核 → 已撤回 | 40301,40901 | skeleton |
| POST | `/club-registration-applications/{application_id}/review` | FR-05 | R03 | ReviewRequest | Application/Club/R02 grant | 待审核 → 已通过/已驳回 | 40301,40901 | skeleton |
| GET | `/clubs` | FR-04 | 登录用户按既有权限 | page,page_size | PageData<Club> | 无 | 40101 | skeleton |
| GET | `/clubs/{club_id}` | FR-04 | 登录用户按既有权限 | 无 | Club | 社团存在 | 40401 | skeleton |
| PATCH | `/clubs/{club_id}` | FR-04 | 目标社团 R02 | PayloadRequest | Club | 社团存在 | 40302,40401 | skeleton |

注册通过必须在一个事务中创建 Club 并授予申请人该 Club 的 R02；驳回不得创建获准 Club 或授权。

## 5. Annual reviews（M02）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| POST | `/annual-reviews` | FR-06 | 目标社团 R02 | PayloadRequest | AnnualReviewApplication | 新建为草稿 | 40302,40902 | skeleton |
| GET | `/annual-reviews` | FR-06,FR-07 | R02 本社团或 R03 全部 | page,page_size | PageData<Application> | 无 | 40301,40302 | skeleton |
| PATCH | `/annual-reviews/{application_id}` | FR-06 | 目标社团 R02 | PayloadRequest | Application | 草稿/已撤回可编辑 | 40302,40901 | skeleton |
| POST | `/annual-reviews/{application_id}/submit` | FR-06 | 目标社团 R02 | 无 | Application | 草稿/已撤回 → 待审核 | 40302,40901 | skeleton |
| POST | `/annual-reviews/{application_id}/withdraw` | FR-06 | 提交社团 R02 | 无 | Application | 待审核 → 已撤回 | 40302,40901 | skeleton |
| POST | `/annual-reviews/{application_id}/review` | FR-07 | R03 | ReviewRequest | Application | 待审核 → 已通过/已驳回 | 40301,40901 | skeleton |

驳回只保存状态/意见并触发 FR-19 通知，不冻结社团或限制其他业务。

## 6. Members（M03）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| POST | `/membership-applications` | FR-08 | R01 本人 | PayloadRequest | MembershipApplication | 目标关系满足申请类型 | 40002,40902 | skeleton |
| GET | `/membership-applications` | FR-08,FR-09 | R01 本人或目标社团 R02 | page,page_size | PageData<Application> | 无 | 40302 | skeleton |
| POST | `/membership-applications/{application_id}/withdraw` | FR-08 | R01 申请本人 | 无 | Application | 待处理 → 已撤回 | 40301,40901 | skeleton |
| POST | `/membership-applications/{application_id}/process` | FR-09 | 目标社团 R02 | ReviewRequest | Application/Member | 待处理 → 已同意/已驳回 | 40302,40901 | skeleton |
| GET | `/clubs/{club_id}/members` | FR-10 | 目标社团 R02；成员按允许范围 | page,page_size | PageData<ClubMember> | 无 | 40302,40401 | skeleton |
| PATCH | `/clubs/{club_id}/members/{member_id}` | FR-10 | 目标社团 R02 | PayloadRequest | ClubMember | 有效成员 | 40302,40401,40901 | skeleton |

## 7. Activities（M04）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| POST | `/activities` | FR-11 | 目标社团 R02 | ActivityCreateRequest | Activity | 新建审核状态草稿 | 40302,40001 | skeleton |
| GET | `/activities` | FR-14 | 登录用户按可见范围 | page,page_size | PageData<Activity> | 无 | 40101 | skeleton |
| GET | `/activities/{activity_id}` | FR-14 | 登录用户按可见范围 | 无 | Activity | 活动存在 | 40401 | skeleton |
| PATCH | `/activities/{activity_id}` | FR-11 | 目标社团 R02 | PayloadRequest | Activity | 审核状态草稿/已撤回 | 40302,40901 | skeleton |
| POST | `/activities/{activity_id}/submit` | FR-12 | 目标社团 R02 | 无 | Activity | 草稿/已撤回 → 待审核 | 40302,40901 | skeleton |
| POST | `/activities/{activity_id}/withdraw` | FR-12 | 提交社团 R02 | 无 | Activity | 待审核 → 已撤回 | 40302,40901 | skeleton |
| POST | `/activities/{activity_id}/review` | FR-13 | R03 | ReviewRequest | Activity | 待审核 → 已通过/已驳回 | 40301,40901 | skeleton |
| POST | `/activities/{activity_id}/publish` | FR-14 | 目标社团 R02 | 无 | Activity | 已通过且未发布 → 报名中 | 40302,40901 | skeleton |
| POST | `/activities/{activity_id}/registrations` | FR-15 | R01 本人 | 无 | ActivityRegistration | 报名中、未超期/容量 | 40901,40902 | skeleton |
| DELETE | `/activities/{activity_id}/registrations/me` | FR-15 | R01 报名本人 | 无 | EmptyObject | 已报名且允许取消 | 40401,40901 | skeleton |
| GET | `/activities/{activity_id}/registrations` | FR-15 | 目标社团 R02 | page,page_size | PageData<Registration> | 活动存在 | 40302,40401 | skeleton |
| POST | `/activities/{activity_id}/cancel` | FR-16 | 目标社团 R02 | ReasonRequest | Activity | 执行阶段且非已结束/已取消 → 已取消 | 40302,40901 | skeleton |
| POST | `/activities/{activity_id}/end` | FR-16 | 目标社团 R02 | PayloadRequest(summary) | Activity | 允许状态 → 已结束 | 40302,40901 | skeleton |

取消后禁止报名并通过 FR-19 通知已报名用户；R03 可查询但 V0.1 契约不提供强制取消 endpoint；不处理退款、场地释放或票务。

## 8. Finance（M05）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| GET | `/finance-records/summary` | FR-18 | 目标社团 R02 或 R03 全部 | club_id,date_from,date_to | FinanceSummary | 无 | 40301,40302 | implemented |
| POST | `/finance-records` | FR-17 | 目标社团 R02 | FinanceRecordCreateRequest | FinanceRecord | 金额/类型有效 | 40001,40302 | implemented |
| GET | `/finance-records` | FR-18 | 目标社团 R02 或 R03 全部 | filters,page,page_size | PageData<FinanceRecord> | 无 | 40301,40302 | implemented |
| PATCH | `/finance-records/{record_id}` | FR-17 | 目标社团 R02 | FinanceRecordUpdateRequest | FinanceRecord | 有效记录 | 40302,40901 | implemented |
| POST | `/finance-records/{record_id}/void` | FR-17 | 目标社团 R02 | ReasonRequest | FinanceRecord | 有效 → 已作废 | 40302,40901 | implemented |

经费只记录、查询、汇总、统计和作废；无审批、报销、支付或财务结算。

### 8.1 M05 领域请求与过滤（implemented）

- 创建：`club_id`、`activity_id?`、`record_type`（`INCOME`/`EXPENSE`）、`amount`（> 0，最多 12 位、2 位小数）、`occurred_on`、`description`（1～500）、`voucher_reference?`（≤255）。
- 修改：仅可修改 `activity_id?`、`record_type?`、`amount?`、`occurred_on?`、`description?`、`voucher_reference?`；仅 `ACTIVE` 记录可改，不能改 `club_id` 或 `status`。`record_type`、`amount`、`occurred_on`、`description` 显式传 `null` 返回 `40002`。
- 列表过滤：`club_id`、`activity_id`、`record_type`、`status`（`ACTIVE`/`VOIDED`）、`date_from`、`date_to`（按 `occurred_on`，含首尾日期）、`page`、`page_size`。
- 范围：R02 未指定 `club_id` 时使用其全部有效社团；指定时必须为本人负责社团；R03 未指定时使用全部社团。
- 汇总过滤：`club_id`、`date_from`、`date_to`；仅 `ACTIVE` 记录计入收入/支出/结余，另返回有效记录数与已作废数。
- `FinanceRecord` 返回 `club_name`、`activity_title`、`created_by_name`、`voided_by_name` 等展示字段；`amount` 以十进制字符串返回，便于保持精度。
- 关联 `activity_id` 必须属于同一 `club_id`，否则 `40002`。

## 9. Notifications（M06）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| GET | `/notifications` | FR-19 | 当前用户本人 | page,page_size,read_status | PageData<Notification> | 无 | 40101 | implemented |
| POST | `/notifications/{notification_id}/read` | FR-19 | 收件人本人 | 无 | Notification | 未读 → 已读 | 40301,40401 | implemented |
| POST | `/notifications/read-all` | FR-19 | 当前用户本人 | 无 | EmptyObject | 无 | 40101 | implemented |
| POST | `/notifications/management` | FR-20 | R03 | ManagementNotificationRequest | NotificationBatchResult | 目标范围有效 | 40001,40301 | implemented |

当前只提供站内通知，不定义邮件、短信或外部消息接口。

### 9.1 M06 领域请求与目标范围（implemented）

- 列表仅返回 `recipient_user_id` 等于当前用户的记录，支持 `read_status`（`UNREAD`/`READ`）过滤，按创建时间倒序。
- 标记已读仅允许收件人本人；重复标记同一通知保持成功且不改变业务含义。
- 管理通知 `target_type`：
  - `USERS`：`user_ids` 非空，其余目标列表必须为空；
  - `ROLES`：`role_codes` 非空（`R01`/`R02`/`R03`/`R04`），其余目标列表必须为空；`R02` 解析为全部有效社团负责人授权；
  - `CLUBS`：`club_ids` 非空，接收人为目标社团有效成员与该社团有效 R02 负责人，去重后发送。
- 返回 `{created_count,recipient_count,target_type}`；目标不存在或无接收人返回 `40002`。
- FR-19 业务事件通过 `app.services.notification_service.notify` / `notify_many` 写入，供成员 A/B 在审核、报名、取消等流程复用；不新增外部通知渠道。

## 10. Reports and audit（M07）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| GET | `/reports/summary` | FR-21 | R02 本社团或 R03 全部 | filters | ReportSummary | 无 | 40301,40302 | implemented |
| GET | `/reports/export` | FR-21 | R02 本社团或 R03 全部 | format=csv,filters | 文件流 | 无 | 40001,40301,40302 | implemented |
| GET | `/audit-logs` | FR-22 | R04 | page,page_size,filters | PageData<AuditLog> | 无 | 40301 | implemented |

### 10.1 M07 统计与导出（implemented）

- `/reports/summary` 支持 `club_id`、`date_from`、`date_to`，返回社团数、有效成员数、活动数、有效报名数、活动审核/执行状态分布，以及经费收入、支出、结余和作废记录数。R02 未指定 `club_id` 时聚合其全部有效社团；R03 未指定时聚合全部社团。
- 日期口径：活动按 `starts_at`、经费按 `occurred_on`、报名按所属活动开始时间；成员数为当前 `ACTIVE` 成员，不受日期过滤影响。
- `/reports/export` 仅支持 `format=csv`，其他格式返回 `40001`。导出内容为经费明细并附带汇总头；使用 UTF-8 BOM、CRLF 和公式注入防护，便于 Excel 打开。权限与经费列表一致。
- `/audit-logs` 仅 R04 可访问，支持 `actor_user_id`、`action`、`resource_type`、`date_from`、`date_to`、`page`、`page_size`；`detail` 返回解析后的 JSON 或原始文本。
- 审计写入统一使用 `app.services.audit_service.record_audit`；成员 C 已为经费创建/修改/作废和管理通知发布写入审计，成员 A/B/负责人可在审核、授权等关键操作中复用。

## 11. 契约变更规则

- 不得由成员私自改变 URL、method、FR 映射、角色或资源归属语义。
- 领域 request/response 字段细化可以通过 PR 完成，但不得扩大 V1.1 范围。
- 发现需求矛盾时记录到 `ENGINEERING_ISSUES_V0_1.md`；需改需求则标记 `REQUIRES_CR`。
