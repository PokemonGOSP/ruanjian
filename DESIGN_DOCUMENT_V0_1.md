# 高校社团活动管理系统——Engineering Design V0.1

> 设计输入：`REQUIREMENTS_BASELINE_V1_1.md`。
>
> 本文是课程级 Engineering Skeleton 设计，不实现 M02～M07 业务；业务端点在 V0.1 中保留契约和 501 占位，用于指导后续并行实现与测试。

## 1. 设计目标与约束

设计目标是用规模适中的 B/S 架构支撑 FR-01～FR-23 的实现边界，使权限、状态、数据关系和接口可以独立验证。设计不引入微服务、消息队列、Redis、Kubernetes、真实学校 SSO、支付或外部通知平台。

设计约束：MySQL 8、浏览器访问、统一 `/api/v1` 接口前缀、JWT 会话、自建/预置测试账号、R02 必须绑定具体 Club、所有状态转换由服务层校验。

## 2. 总体架构

### 2.1 逻辑架构

```text
Vue 3 SPA
  ├─ Vue Router：页面路由和登录保护
  ├─ Pinia auth store：token、/auth/me、当前用户
  └─ Axios client：Base URL、Bearer、统一错误处理
             │ HTTP/JSON
             ▼
FastAPI API Layer
  ├─ Router：路径、参数、响应模型
  ├─ Dependency/Auth：JWT 解析、账号状态、R01/R02/R03/R04 权限
  ├─ Service：状态机、业务规则、事务边界
  └─ Repository/SQLAlchemy：查询、写入、分页、聚合
             │ PyMySQL / SQLAlchemy
             ▼
MySQL 8 / InnoDB
```

职责与依赖方向固定为：View → API client → FastAPI Router → Dependency/Service → Repository/Model → MySQL。上层不得直接绕过 Service 修改状态或绕过权限查询数据。

### 2.2 部署与运行视图

```text
开发者浏览器 :5173
        │ CORS / HTTP
        ▼
Vite 开发服务器或构建后的静态站点
        │ /api/v1
        ▼
FastAPI/Uvicorn :8000
        │ DATABASE_URL / utf8mb4
        ▼
Docker Compose MySQL 8.4 :3306
```

课程环境使用 Docker Compose 提供 MySQL；Alembic 负责结构迁移，Seed 负责本地虚构测试数据。生产级反向代理、横向扩容和高可用不在本课程范围内。

## 3. 模块设计与边界

| 模块 | 职责 | 主要接口/数据 | 负责人 |
|---|---|---|---|
| M01 身份与权限 | 登录、退出、账号状态、JWT、系统角色、Club 级 R02、审计入口 | `/auth/*`、`/accounts/*`；users、role assignments、revoked_tokens | Leader |
| M02 社团注册与年审 | 注册申请、审核、Club 创建、年审提交和审核 | `/club-registration-applications*`、`/annual-reviews*`；clubs 及申请表 | A |
| M03 成员管理 | 入团/退团、成员处理、名册和职务 | `/membership-applications*`、`/clubs/{id}/members*` | A |
| M04 活动管理 | 活动申请、审核、发布、报名、取消、结束、归档 | `/activities*`；activities、registrations | B |
| M05 经费记录 | 收支记录、查询、汇总、作废和历史追踪 | `/finance-records*`；finance_records | C |
| M06 通知中心 | 站内通知、已读、业务事件通知和管理通知 | `/notifications*`；notifications | C |
| M07 统计与审计 | 统计、CSV 导出、关键操作审计查询 | `/reports*`、`/audit-logs`；聚合查询、audit_logs | C |

公共组件由 Leader 维护：响应 Envelope、错误码、JWT、权限依赖、全局异常、数据库 Session、Alembic 和公共枚举。模块不得重复创建 User、JWT、权限或响应格式。

## 4. 接口设计

### 4.1 通用约定

- Base URL：`/api/v1`。
- JSON 成功：`{"code":0,"message":"success","data":...}`。
- JSON 失败：`{"code":<业务错误码>,"message":"原因","data":null}`。
- 认证：除 health、login 外使用 `Authorization: Bearer <JWT>`。
- 分页输入：`page` 从 1 开始，`page_size` 为 1～100；输出 `{items,page,page_size,total}`。
- 资源 ID 使用正整数；日期时间使用 ISO 8601；金额使用两位小数且非负。
- 主要错误：40001 输入无效、40101 无效/缺失 token、40104 账号不可用、40301 系统权限不足、40302 Club 权限不足、40401 资源不存在、40901 状态冲突、40902 唯一性冲突、50000 数据库/服务异常、50101 Skeleton 未实现。

### 4.2 已实现公共接口

| 方法/接口 | 用途 | 输入 | 输出 | 限制/错误 |
|---|---|---|---|---|
| GET `/health` | 检查服务和 DB | 无 | `{service,database}` | 不要求登录；数据库故障返回降级信息 |
| POST `/auth/login` | 登录并签发 JWT | `{username,password}` | `{access_token,token_type,expires_in}` | 账号不存在、密码错误、停用账号拒绝 |
| POST `/auth/logout` | 撤销当前 JWT | Bearer token | 空对象 | token 无效或已撤销拒绝 |
| GET `/auth/me` | 获取当前用户和授权摘要 | Bearer token | user_id、username、display_name、system_roles、club_authorizations | 检查 token、账号状态和撤销记录 |

### 4.3 业务接口族

完整方法/路径/FR/角色/schema 对照见 `docs/api/API_CONTRACT_V0_1.md`。接口族边界如下：

| 接口族 | 典型接口 | 关键输入/输出 | 主要权限 |
|---|---|---|---|
| 账号授权 | `/accounts`、`/accounts/{id}/role-assignments` | Account、RoleAssignment | R04；R02 授权必须有 club_id |
| 注册审核 | `/club-registration-applications`、`/{id}/review` | PayloadRequest、ReviewRequest、Application/Club/R02 grant | R01 本人、R03 审核 |
| 年审 | `/annual-reviews`、`/{id}/withdraw`、`/{id}/review` | 年度材料、ReviewRequest | 对应 Club 的 R02、R03 |
| 成员 | `/membership-applications`、`/clubs/{id}/members` | JOIN/EXIT、处理意见、成员职务 | R01 本人、目标 Club R02 |
| 活动 | `/activities`、`/{id}/review/publish/cancel/end` | ActivityCreate、Reason、ReviewRequest、状态资源 | Club R02、R03、R01 报名 |
| 经费 | `/finance-records`、`/summary`、`/{id}/void` | 类型、金额、时间、凭证、筛选条件 | Club R02 或 R03 |
| 通知 | `/notifications`、`/read-all`、`/management` | 收件人、事件、已读状态 | 本人；R03 管理通知 |
| 报表审计 | `/reports/summary`、`/export`、`/audit-logs` | 过滤条件、CSV 格式、分页 | R02 仅本 Club，R03 全业务，R04 审计 |

### 4.4 外部接口

当前没有必需的第三方接口。学校统一身份认证、邮件/短信、财务系统和支付系统仅作为未来可能集成的外部系统，不在当前接口契约中虚构 URL、协议或字段。

## 5. 数据设计

### 5.1 核心实体与字段

| 实体/表 | 关键字段 | 约束与用途 |
|---|---|---|
| users | id、username、password_hash、display_name、status | username 唯一；status 为 NORMAL/DISABLED；密码只存哈希 |
| system_role_assignments | user_id、role_code、active、granted_by | user_id+role_code 唯一；只表达 R01/R03/R04 |
| club_role_assignments | user_id、club_id、role_code、active | user_id+club_id+role_code 唯一；R02 的 Club 级授权来源 |
| club_registration_applications | applicant_user_id、proposed_name、review_status、reviewed_by | 申请人外键；状态为 DRAFT/PENDING/APPROVED/REJECTED/WITHDRAWN |
| clubs | registration_application_id、name、description | registration_application_id 和 name 唯一；审核通过后创建 |
| annual_review_applications | club_id、review_year、materials、review_status | club_id+review_year 唯一；R02 提交、R03 审核 |
| club_members | club_id、user_id、position_name、status | club_id+user_id 唯一；成员关系不是全局角色 |
| membership_applications | club_id、applicant_user_id、application_type、status | JOIN/EXIT；处理人和处理意见可追踪 |
| activities | club_id、title、starts_at、ends_at、capacity、budget、review_status、execution_status | 活动审核状态与执行状态分离；Club 外键 |
| activity_registrations | activity_id、user_id、status | activity_id+user_id 唯一；报名/取消保留记录 |
| finance_records | club_id、activity_id、record_type、amount、occurred_on、status | 金额 DECIMAL(12,2)；INCOME/EXPENSE；作废不删除 |
| notifications | recipient_user_id、event_type、related_type/id、read_status | 收件人外键；UNREAD/READ |
| audit_logs | actor_user_id、action、resource_type/id、detail_json、created_at | 关键操作追加记录，不由普通用户删除 |
| revoked_tokens | jti、user_id、expires_at、revoked_at | jti 唯一；logout 后阻止 token 继续使用 |

### 5.2 一致性策略

- 外键约束保证用户、Club、申请、活动和成员关系不悬空。
- 唯一约束防止重复账号、重复角色授权、重复年度年审、重复成员和重复报名。
- FR-05 通过、Club 创建和申请人 R02 授权必须在同一事务中完成；失败则整体回滚。
- 状态转换由 Service 层校验，数据库只接受合法枚举值；终态不允许逆向转换。
- 账号停用、权限撤销、经费作废保留历史，不删除业务记录。
- schema 变化只通过 Alembic；当前 revision 为 `20260915_0001`。

## 6. 关键流程与异常处理

### 6.1 社团注册审核

```text
R01 填写草稿
  → 提交：DRAFT → PENDING
  → R03 审核
      ├─ 通过：创建 Club + 授予申请人该 Club 的 R02 + 通知
      └─ 驳回：REJECTED + 保存意见 + 通知，不创建 Club、不授权
```

异常：缺少必填字段返回 40001；非本人编辑/撤回返回 40301；非 R03 审核返回 40301；重复审核返回 40901；事务任一写入失败全部回滚。

### 6.2 年审与申请撤回

R02 只能撤回本人所属 Club 提交且处于 PENDING 的年审/活动申请；R01 只能撤回本人提交且处于 PENDING 的注册申请；APPROVED/REJECTED 不可撤回。年审驳回只保存意见和通知，不自动冻结 Club 或其他业务。

### 6.3 活动生命周期

```text
DRAFT → PENDING → APPROVED → UNPUBLISHED → REGISTRATION_OPEN
                                  ├→ REGISTRATION_CLOSED → IN_PROGRESS → ENDED → ARCHIVED
                                  └→ CANCELLED
```

审核状态和执行状态分列。R02 只能取消本 Club 活动，必须填写原因；取消后关闭报名并通知已报名用户；已结束活动不能取消。重复发布、非法状态转换、跨 Club 操作均返回对应错误，不写入部分结果。

### 6.4 登录与停用账号

```text
登录请求 → 查询账号 → 校验 status 和密码
  ├─ 成功：签发 JWT
  └─ 失败：统一 401，不泄露账号是否存在的额外信息
logout → 将 jti 写入 revoked_tokens → 后续受保护请求拒绝
```

### 6.5 故障模式与恢复

| 故障 | 检测 | 处理 | 恢复 |
|---|---|---|---|
| MySQL 不可用 | health 查询失败/SQLAlchemy 异常 | 返回统一 50000 或降级 health，不泄露连接串 | 恢复 MySQL 后重试；不切换 SQLite |
| 重复提交 | 唯一约束或状态检查 | 返回 40901/40902，保留原记录 | 用户修正输入或等待状态变化 |
| 并发状态冲突 | 更新前重新读取当前状态 | 拒绝过期操作，返回 40901 | 重新加载后重试 |
| 权限不足 | dependency/Club scope 检查 | 返回 401/403，不返回被保护数据 | 使用正确角色或资源 |
| 事务中途失败 | Service 捕获异常/事务回滚 | 整体回滚并记录服务错误 | 修复输入或数据库后重试 |

## 7. 界面与交互设计

### 7.1 页面结构

- LoginView：用户名、密码、错误提示、登录按钮。
- AppLayout：当前用户、身份摘要、退出入口和按角色显示的导航。
- DashboardView：当前用户、system roles、R02 Club 授权摘要和通知入口。
- Clubs/Members/Activities/Finance/Notifications/Reports/Accounts：V0.1 提供路由与占位；后续 owner 按契约实现。

### 7.2 角色交互要点

- R01：突出本人申请、可浏览活动、报名和通知；不可见或不可操作审核控件。
- R02：先选择已授权 Club，再显示该 Club 的资料、成员、年审、活动和经费；跨 Club 请求必须明确拒绝。
- R03：提供待审核列表、意见输入和全体业务查询；不显示账号技术管理入口。
- R04：提供账号状态、系统角色、Club 级 R02 授权和审计查询；不提供业务审核替代入口。

### 7.3 表单与可用性

所有必填字段有标记；金额、容量、时间范围和文本长度在客户端提示并由服务端再次校验；成功/失败使用统一 message；分页、空列表、加载中、权限拒绝和数据库异常均有明确反馈。

## 8. 非功能设计

| 目标 | 设计应对 | 验证思路 |
|---|---|---|
| 性能 | 分页、索引、聚合查询；常用接口不返回无关字段 | 10 并发、P95 ≤2s；统计 P95 ≤5s |
| 安全 | PBKDF2-SHA256、HS256 JWT、Bearer、账号状态检查、Club scope、统一错误 | 未登录/越权/停用账号测试；扫描提交文件中的 secret |
| 可靠性 | Service 事务、状态机、外键和唯一约束、health、审计 | 注入重复/并发/DB 故障并检查回滚 |
| 可维护性 | Router/Dependency/Service/Repository 分层，FR/AC/CR 编号追踪 | 代码结构检查、需求追溯检查 |
| 兼容性 | Vue SPA + 标准 JSON/HTTP，支持 Chrome/Edge | 浏览器手工验收和前端 build |
| 可扩展性 | 模块按 M01～M07 隔离；外部 SSO/通知留接口边界而不提前实现 | 新增模块不修改公共授权和响应语义 |

## 9. 设计决策与权衡

| 决策 | 选择 | 权衡 |
|---|---|---|
| 单体分层而非微服务 | FastAPI + SQLAlchemy + MySQL | 牺牲独立扩展，换取课程规模内低部署复杂度和易调试 |
| R02 Club 级授权 | 独立 `club_role_assignments` | 查询需携带 club scope，但避免全局角色越权 |
| JWT + 撤销表 | 无状态 token 配合 `revoked_tokens` | 比服务端 session 简单，但需检查撤销和过期 |
| 单级 R03 审核 | 一个业务审核角色 | 不模拟未知真实多级制度，降低复杂度；真实层级待核实 |
| 站内通知 | 不接第三方消息 | 可测试、无外部依赖，但不保证短信/邮件送达 |
| 记录型经费 | 不做支付/报销 | 满足课程题目且避免伪造真实财务流程 |
| Skeleton 先行 | 52 个端点先保留契约/501 | 并行开发接口稳定，但 V0.1 尚未完成 M02～M07 |

## 10. 测试考虑

### 10.1 测试层次

- 单元测试：密码哈希、JWT 编解码、状态转换、权限判断、错误映射。
- API 集成测试：真实 MySQL migration/seed 后测试 login、health、`/auth/me` 和核心业务端点。
- 权限测试：R01/R02/R03/R04、跨 Club、本人/非本人、停用账号。
- 状态测试：每个正常转换、重复操作、终态逆向转换、撤回与取消区别。
- 数据测试：唯一约束、外键、金额/时间范围、事务回滚、历史保留。
- 前端测试：登录、token storage、路由 guard、`/auth/me`、角色导航、API 错误展示。

### 10.2 关键验收用例

| 用例 | 预期 |
|---|---|
| R01 注册通过 | Club 创建、申请人获得该 Club R02、通知生成 |
| R01 不能撤回他人申请 | 403/业务拒绝，状态不变 |
| Club A R02 访问 Club B | 拒绝且不泄露数据 |
| R03 审核活动 | 审核状态改变，意见保存，发布前不能报名 |
| 活动取消 | 必填原因、状态变更、报名关闭、通知产生 |
| R04 停用账号 | 新登录失败，历史业务数据保留 |
| DB 故障 | health 为 down/degraded，接口不泄露连接信息 |

## 11. 需求追溯与提交材料

需求基线沿用实验 1 的 `REQUIREMENTS_BASELINE_V1_1.md`，不在本文重新定义需求。完整映射见 `REQUIREMENTS_TRACEABILITY.md`；AI 协作和人工核实见 `AI_COLLABORATION_RECORD.md`、`MANUAL_VERIFICATION_NOTES.md`；V1→V1.1 的需求变更见 `CHANGE_REQUESTS_ROUND3.md`。

设计阶段未新增或修改 R/M/FR。若后续实现发现必须改变需求含义，必须提交 CR，而不是直接修改本文或基线。
