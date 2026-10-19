# API 字段级 Schema 目录 V0.1

> 本目录替代接口表中的 `PayloadRequest` 作为后续实现的领域请求定义；每个业务端点按其动作引用相应 Schema。所有字符串 UTF-8，未知字段拒绝为 40001。

| Schema | 字段与约束 |
|---|---|
| ClubRegistrationRequest | `proposed_name` string 1..150、`description` 1..5000、`advisor_contact` 1..255 可空。 |
| ClubProfileUpdate | `name` 1..150 可空、`description` 1..5000 可空、`advisor_contact` 1..255 可空；至少一个字段。 |
| AnnualReviewRequest | `club_id` positive int、`review_year` 2000..2100、`materials` 为数据字典 §3 的 JSON。 |
| MembershipApplicationRequest | `club_id` positive int、`application_type` JOIN/EXIT、`reason` 1..2000 可空。 |
| MemberUpdateRequest | `position_name` 1..100 可空、`status` ACTIVE/EXITED 可空；至少一个字段。 |
| FinanceRecordRequest | `club_id` positive int、`activity_id` positive int 可空、`record_type` INCOME/EXPENSE、`amount` decimal(12,2) >0、`occurred_on` ISO-8601、`description` 1..500、`voucher_reference` 1..255 可空、`attachments` 0..5（PDF/JPEG/PNG，各 ≤10 MiB）。 |
| ManagementNotificationRequest | `target_type` USER/ROLE/CLUB、`target_ids` 1..1000 个正整数、`title` 1..200、`content` 1..5000。 |
| ActivityEndRequest | `summary` 1..5000。 |
| ReviewRequest | `decision` APPROVED/REJECTED；`comment` 通过时可空、驳回时 1..2000。 |
| ReasonRequest | `reason` 1..2000。 |

可见性：`GET /clubs/{id}` 与 `/activities*` 的 R01 仅返回已获准且对学生可见/报名中的活动；R02 仅所授权 Club；R03 全部业务；R04 不具业务详情入口。分页 GET 的过滤字段必须组合到权限条件，不能只依赖前端隐藏。

幂等与限流：创建申请/报名使用唯一约束兜底；状态操作以当前状态作条件更新。V0.1 尚未实现请求幂等键或登录限流，契约明确标为实现待办，不能声称已具备。
