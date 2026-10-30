# M02 / M03 API 说明

> Base URL：`/api/v1`；除登录/健康外均需 `Authorization: Bearer <JWT>`。
> 成功：`{"code":0,"message":"success","data":...}`；失败：`{"code":<code>,"message":"...","data":null}`。
> 本文件只细化字段，不改变 `docs/api/API_CONTRACT_V0_1.md` 的路径、method、FR 映射和角色归属。

## 1. 端点总览

| Method | Endpoint | FR | 权限 | 请求 | 响应 data |
|---|---|---|---|---|---|
| POST | `/club-registration-applications` | FR-03 | R01 本人 | `ClubRegistrationCreateRequest` | `ClubRegistrationApplicationData` |
| GET | `/club-registration-applications` | FR-03/05 | R01 本人或 R03 全部 | `page,page_size,status?` | `PageData<ClubRegistrationApplicationData>` |
| PATCH | `/club-registration-applications/{id}` | FR-03 | R01 申请本人 | `ClubRegistrationUpdateRequest` | `ClubRegistrationApplicationData` |
| POST | `/club-registration-applications/{id}/submit` | FR-03 | R01 申请本人 | 无 | `ClubRegistrationApplicationData` |
| POST | `/club-registration-applications/{id}/withdraw` | FR-03 | R01 申请本人 | 无 | `ClubRegistrationApplicationData` |
| POST | `/club-registration-applications/{id}/review` | FR-05 | R03 | `ReviewRequest` | `ClubRegistrationReviewResult` |
| GET | `/clubs` | FR-04 | 登录用户 | `page,page_size` | `PageData<ClubData>` |
| GET | `/clubs/{club_id}` | FR-04 | 登录用户 | 无 | `ClubData` |
| PATCH | `/clubs/{club_id}` | FR-04 | 目标社团 R02 | `ClubUpdateRequest` | `ClubData` |
| POST | `/annual-reviews` | FR-06 | 目标社团 R02 | `AnnualReviewCreateRequest` | `AnnualReviewData` |
| GET | `/annual-reviews` | FR-06/07 | R02 本社团或 R03 全部 | `page,page_size,club_id?,review_year?,status?` | `PageData<AnnualReviewData>` |
| PATCH | `/annual-reviews/{id}` | FR-06 | 目标社团 R02 | `AnnualReviewUpdateRequest` | `AnnualReviewData` |
| POST | `/annual-reviews/{id}/submit` | FR-06 | 目标社团 R02 | 无 | `AnnualReviewData` |
| POST | `/annual-reviews/{id}/withdraw` | FR-06 | 目标社团 R02 | 无 | `AnnualReviewData` |
| POST | `/annual-reviews/{id}/review` | FR-07 | R03 | `ReviewRequest` | `AnnualReviewData` |
| POST | `/membership-applications` | FR-08 | R01 本人 | `MembershipApplicationCreateRequest` | `MembershipApplicationData` |
| GET | `/membership-applications` | FR-08/09 | R01 本人或目标社团 R02 | `page,page_size,scope?,club_id?,status?,application_type?` | `PageData<MembershipApplicationData>` |
| POST | `/membership-applications/{id}/withdraw` | FR-08 | R01 申请本人 | 无 | `MembershipApplicationData` |
| POST | `/membership-applications/{id}/process` | FR-09 | 目标社团 R02 | `ReviewRequest` | `MembershipProcessResult` |
| GET | `/clubs/{club_id}/members` | FR-10 | 目标社团 R02；有效成员仅本人记录 | `page,page_size,status?` | `PageData<ClubMemberData>` |
| PATCH | `/clubs/{club_id}/members/{member_id}` | FR-10 | 目标社团 R02 | `ClubMemberUpdateRequest` | `ClubMemberData` |

## 2. 请求字段

### 2.1 通用审核

`ReviewRequest`（沿用公共 Schema）：

```json
{"decision": "APPROVED", "comment": "材料齐全"}
```

- `decision`：`APPROVED` / `REJECTED`。
- `comment`：可选，≤2000；注册审核、年审审核选择 `REJECTED` 时必填且不能全为空白。
- 成员申请处理：`comment` 可选。

### 2.2 社团注册

`ClubRegistrationCreateRequest`：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `proposed_name` | string | 是 | 1～150，去首尾空白后非空 |
| `description` | string | 是 | 1～10000，去首尾空白后非空 |
| `advisor_contact` | string/null | 否 | ≤255；空串归一为 `null` |

`ClubRegistrationUpdateRequest`：同字段全部可选，但 `proposed_name` / `description` 显式 `null` 会校验失败；`advisor_contact` 显式 `null` 表示清空。

### 2.3 社团资料

`ClubUpdateRequest`：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `name` | string | 否 | ≤150，非空；全局唯一 |
| `description` | string | 否 | ≤10000，非空 |
| `advisor_contact` | string/null | 否 | ≤255；`null` 清空 |

### 2.4 年审

`AnnualReviewCreateRequest`：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `club_id` | integer | 是 | ≥1；调用者必须是该社团 R02 |
| `review_year` | integer | 是 | 2000～2100 |
| `materials` | string | 是 | 1～20000，去空白后非空 |

`AnnualReviewUpdateRequest`：`review_year`、`materials` 可选；`materials` 显式 `null` 校验失败。

### 2.5 成员申请

`MembershipApplicationCreateRequest`：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `club_id` | integer | 是 | ≥1；社团必须存在 |
| `application_type` | string | 是 | `JOIN` / `EXIT` |
| `reason` | string/null | 否 | ≤2000；空串归一为 `null` |

`ClubMemberUpdateRequest`：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `position_name` | string/null | 是（至少传该字段） | ≤100；`null` 清空职务 |

## 3. 响应字段

### 3.1 `ClubRegistrationApplicationData`

```json
{
  "id": 11,
  "applicant_user_id": 1,
  "applicant_display_name": "学生一",
  "proposed_name": "星河读书社",
  "description": "虚构社团简介",
  "advisor_contact": "teacher@example.com",
  "review_status": "DRAFT",
  "review_comment": null,
  "reviewed_by": null,
  "submitted_at": null,
  "reviewed_at": null,
  "created_at": "2026-01-01T09:00:00"
}
```

`review_status` 固定为 `DRAFT/PENDING/APPROVED/REJECTED/WITHDRAWN`。

### 3.2 `ClubRegistrationReviewResult`

```json
{
  "application": {"id": 11, "review_status": "APPROVED", "...": "..."},
  "club": {
    "id": 1,
    "registration_application_id": 11,
    "name": "星河读书社",
    "description": "虚构社团简介",
    "advisor_contact": "teacher@example.com",
    "created_at": "2026-01-02T10:00:00",
    "updated_at": "2026-01-02T10:00:00"
  },
  "club_authorization": {"club_id": 1, "user_id": 1, "role_code": "R02"}
}
```

- 通过时 `club`、`club_authorization` 非空。
- 驳回时两者均为 `null`。
- 不会返回全局 `R02` 角色；授权只针对该 `club_id`。

### 3.3 `ClubData`

字段：`id`、`registration_application_id`、`name`、`description`、`advisor_contact`、`created_at`、`updated_at`。

### 3.4 `AnnualReviewData`

字段：`id`、`club_id`、`club_name`、`review_year`、`submitted_by`、`submitter_display_name`、`materials`、`review_status`、`review_comment`、`reviewed_by`、`submitted_at`、`reviewed_at`、`created_at`。

### 3.5 `MembershipApplicationData`

字段：`id`、`club_id`、`club_name`、`applicant_user_id`、`applicant_display_name`、`application_type`、`reason`、`status`、`processed_by`、`processed_by_display_name`、`process_comment`、`created_at`、`processed_at`。

`status` 固定为 `PENDING/APPROVED/REJECTED/WITHDRAWN`；`application_type` 为 `JOIN/EXIT`。

### 3.6 `MembershipProcessResult`

```json
{
  "application": {"id": 41, "status": "APPROVED", "...": "..."},
  "member": {
    "id": 31,
    "club_id": 1,
    "user_id": 1,
    "username": "student01",
    "display_name": "学生一",
    "position_name": null,
    "status": "ACTIVE",
    "joined_at": "2026-01-02T10:00:00",
    "exited_at": null
  }
}
```

- 驳回或退出时 `member` 也可能为 `null`（驳回）或返回更新后的成员（退出）。
- 不会返回其他社团的成员关系。

### 3.7 `ClubMemberData`

| 字段 | 负责人查看 | 有效成员查看（仅本人） |
|---|---|---|
| `id`, `club_id`, `display_name` | 有 | 有 |
| `position_name`, `status` | 有 | 有 |
| `user_id`, `username` | 有 | `null` |
| `joined_at`, `exited_at` | 有 | `null` |

> 有效成员调用名册接口时，Service 会强制 `user_id=当前用户`、`status=ACTIVE`，因此 `items` 最多一条本人记录；分页 `total` 为 0 或 1。

## 4. 查询参数

| 端点 | 参数 | 说明 |
|---|---|---|
| 所有分页端点 | `page` | 从 1 开始；默认 1 |
| 所有分页端点 | `page_size` | 1～100；默认 20 |
| 注册申请列表 | `status` | 可选，固定 ReviewStatus |
| 年审列表 | `club_id` | 可选；R02 必须是本人负责社团，R03 任意 |
| 年审列表 | `review_year` | 可选，2000～2100 |
| 年审列表 | `status` | 可选，固定 ReviewStatus |
| 成员申请列表 | `scope` | 可选：`mine` 我的申请；`managed` 我负责社团的申请；省略时返回“本人 + 负责社团”的并集 |
| 成员申请列表 | `club_id` | 可选；用于限定社团 |
| 成员申请列表 | `status` | 可选：`PENDING/APPROVED/REJECTED/WITHDRAWN` |
| 成员申请列表 | `application_type` | 可选：`JOIN/EXIT` |
| 成员名册 | `status` | 可选：`ACTIVE/EXITED`；有效成员受限视图强制只返回本人 `ACTIVE` 记录 |

> `status`、`scope`、`application_type` 是对契约分页参数的**可选扩展**，不改变路径或已有语义；如负责人要求严格只保留 `page/page_size`，可删除这些参数及 UI 过滤，不影响主流程。

## 5. 错误码与典型场景

| code | HTTP | M02/M03 典型场景 |
|---|---|---|
| 40001 | 422 | 字段校验失败；驳回未填理由；空 PATCH；非法 `scope` |
| 40002 | 400 | 目标社团不存在；已是成员仍申请入团；非成员申请退出 |
| 40101～40103 | 401 | 未登录、token 失效、账号停用 |
| 40301 | 403 | 缺少 R03/R01；非本人编辑/撤回；申请人与审核/处理人相同 |
| 40302 | 403 | 缺少目标社团 R02；非成员查看名册 |
| 40401 | 404 | 申请/社团/成员/年审不存在 |
| 40901 | 409 | 当前状态不允许（如审核非 `PENDING`、编辑非草稿） |
| 40902 | 409 | 社团名称冲突、年审年度重复、待处理成员申请重复、唯一约束冲突 |

失败响应示例：

```json
{"code": 40302, "message": "没有该社团的 R02 权限", "data": null}
```

## 6. 典型调用序列

### 6.1 社团注册

```http
POST /api/v1/club-registration-applications
Authorization: Bearer <student01>
Content-Type: application/json

{"proposed_name":"星河读书社","description":"虚构社团简介","advisor_contact":null}
```

```http
POST /api/v1/club-registration-applications/11/submit
Authorization: Bearer <student01>
```

```http
POST /api/v1/club-registration-applications/11/review
Authorization: Bearer <manager01>
Content-Type: application/json

{"decision":"APPROVED","comment":"材料齐全"}
```

### 6.2 年审

```http
POST /api/v1/annual-reviews
Authorization: Bearer <leader01>
Content-Type: application/json

{"club_id":1,"review_year":2026,"materials":"虚构年审材料"}
```

```http
POST /api/v1/annual-reviews/21/submit
Authorization: Bearer <leader01>
```

### 6.3 入团

```http
POST /api/v1/membership-applications
Authorization: Bearer <student01>
Content-Type: application/json

{"club_id":1,"application_type":"JOIN","reason":"希望参加读书活动"}
```

```http
POST /api/v1/membership-applications/41/process
Authorization: Bearer <leader01>
Content-Type: application/json

{"decision":"APPROVED","comment":"欢迎"}
```
