# API Contract V0.1

## 1. 通用约定

- Base URL：`/api/v1`
- 认证：`Authorization: Bearer <JWT>`；除 login 和 health 外均需登录。
- 成功：`{"code":0,"message":"success","data":...}`。
- 失败：`{"code":<error_code>,"message":"具体原因","data":null}`。
- 分页：`page` 从 1 开始，`page_size` 为 1～100；响应 `data={items,page,page_size,total}`。
- R02 是目标 `club_id` 的资源级授权，不是全局角色；R03 可按既有 FR 访问系统内全部社团业务记录；R04 不参与业务审核。
- 领域请求字段、长度、枚举与附件白名单见随包提交的 `docs/api/SCHEMA_CATALOG_V0_1.md`；表中历史 `PayloadRequest` 标记一律按该目录对应领域 Schema 实现，不得自行猜测字段。
- Skeleton 路由统一返回 HTTP 501 / code 50101；已实现路由见表中 `implemented`。

主要响应 schema：`TokenData`、`CurrentUserData`、`PageData<T>`、`Resource`（对应领域资源）、`EmptyObject`。主要请求 schema：`LoginRequest`、`AccountCreateRequest`、`AccountUpdateRequest`、`RoleAssignmentRequest`、`ReviewRequest`、`ReasonRequest`、`ActivityCreateRequest`、`PayloadRequest`。

## 2. Health 与认证

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| GET | `/health` | 工程基础 | 公开 | 无 | `{service,database}` | 无 | 50000 | implemented |
| POST | `/auth/login` | FR-01 | 公开；账号须正常 | LoginRequest | TokenData | 正常账号 | 40001,40103,40104 | implemented |
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
| GET | `/finance-records/summary` | FR-18 | 目标社团 R02 或 R03 全部 | club_id/filter | FinanceSummary | 无 | 40302 | skeleton |
| POST | `/finance-records` | FR-17 | 目标社团 R02 | PayloadRequest | FinanceRecord | 金额/类型有效 | 40001,40302 | skeleton |
| GET | `/finance-records` | FR-18 | 目标社团 R02 或 R03 全部 | filters,page,page_size | PageData<FinanceRecord> | 无 | 40302 | skeleton |
| PATCH | `/finance-records/{record_id}` | FR-17 | 目标社团 R02 | PayloadRequest | FinanceRecord | 有效记录 | 40302,40901 | skeleton |
| POST | `/finance-records/{record_id}/void` | FR-17 | 目标社团 R02 | ReasonRequest | FinanceRecord | 有效 → 已作废 | 40302,40901 | skeleton |

经费只记录、查询、汇总、统计和作废；无审批、报销、支付或财务结算。

## 9. Notifications（M06）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| GET | `/notifications` | FR-19 | 当前用户本人 | page,page_size | PageData<Notification> | 无 | 40101 | skeleton |
| POST | `/notifications/{notification_id}/read` | FR-19 | 收件人本人 | 无 | Notification | 未读 → 已读 | 40301,40401 | skeleton |
| POST | `/notifications/read-all` | FR-19 | 当前用户本人 | 无 | EmptyObject | 无 | 40101 | skeleton |
| POST | `/notifications/management` | FR-20 | R03 | PayloadRequest | NotificationBatchResult | 目标范围有效 | 40001,40301 | skeleton |

当前只提供站内通知，不定义邮件、短信或外部消息接口。

## 10. Reports and audit（M07）

| Method | Endpoint | FR | 角色/资源归属 | Request | Response data | 状态要求 | 主要错误 | 实现状态 |
|---|---|---|---|---|---|---|---|---|
| GET | `/reports/summary` | FR-21 | R02 本社团或 R03 全部 | filters | ReportSummary | 无 | 40301,40302 | skeleton |
| GET | `/reports/export` | FR-21 | R02 本社团或 R03 全部 | format=csv,filters | 文件流 | 无 | 40001,40301,40302 | skeleton |
| GET | `/audit-logs` | FR-22 | R04 | page,page_size,filters | PageData<AuditLog> | 无 | 40301 | skeleton |

## 11. 契约变更规则

- 不得由成员私自改变 URL、method、FR 映射、角色或资源归属语义。
- 领域 request/response 字段细化可以通过 PR 完成，但不得扩大 V1.1 范围。
- 发现需求矛盾时记录到 `ENGINEERING_ISSUES_V0_1.md`；需改需求则标记 `REQUIRES_CR`。
