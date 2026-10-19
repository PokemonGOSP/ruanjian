# 实验 1 提交清单（需求分析文档生成 / AI 协作）

> 本清单对应教师要求的三类材料：需求分析文档、AI 协作记录、人工核实说明。建议将下列文件作为同一次提交的多个附件上传，以便评分者能在提交物内部完成编号和过程交叉核对。

## A. 需求分析文档及其可验证附件

| 文件 | 提交目的 |
|---|---|
| `REQUIREMENTS_ANALYSIS_FINAL.md` | 主文档：背景、场景、功能/非功能需求、优先级、范围与边界。 |
| `REQUIREMENTS_BASELINE_V1_1.md` | 冻结需求基线：R/M/FR 编号、术语、状态和范围的完整依据。 |
| `REQUIREMENTS_DATA_DICTIONARY.md` | 字段级输入/输出、格式、取值、错误码与导出约定。 |
| `ACCEPTANCE_CRITERIA_FULL.md` | FR-01～FR-23 的完整编号化验收标准（正常和异常/权限）。 |
| `PERFORMANCE_TEST_BASELINE.md` | NFR-PERF 的测试环境、数据集、工具版本和判定方法。 |
| `USABILITY_COMPATIBILITY_TEST_CHECKLIST.md` | NFR-USE/NFR-COMP 的步骤计数、权限可见性与浏览器验收记录模板。 |
| `REQUIREMENTS_TRACEABILITY.md` | 问题—场景—FR—验收—变更的追溯矩阵。 |

## B. AI 协作记录

| 文件 | 提交目的 |
|---|---|
| `AI_COLLABORATION_RECORD.md` | 三轮提示词、AI 建议、人工采纳/修改/否决汇总。 |
| `AI_REVIEW_NOTES_ROUND1.md` | Round 1 原始建议、备选项与负责人审查结果。 |
| `AI_COLLAB_LOG_ROUND2.md` | Round 2 根据 D01～D08 固化 V1 的过程记录。 |
| `AI_COLLAB_LOG_ROUND3.md` | Round 3 变更和一致性处理的原始过程记录。 |
| `AI_COLLAB_LOG_ROUND4.md` | Round 4 依据评分反馈的状态对齐、NFR 细化和人工改写对照。 |
| `CHANGE_REQUESTS_ROUND3.md` | CR-01～CR-05 的变更提出、影响与处理记录。 |
| `CHANGE_REQUESTS_ROUND4.md` | CR-06～CR-07 的状态对齐与隐私/附件细化记录。 |

## C. 人工核实说明

| 文件 | 提交目的 |
|---|---|
| `MANUAL_VERIFICATION_NOTES.md` | 已做的课程项目设计确认、未做的现实制度核实、核实边界与后续待办。 |

## 提交前核对

- [ ] 不提交 `.env`、数据库导出、真实账号、Token、密码或 SSH 私钥。
- [ ] 不把“待核实”的学校真实制度写成已核实事实。
- [ ] 主文档、基线、完整 AC、数据字典和原始 AI 分轮日志均在同一提交中。
- [ ] 说明这是个人提交：A/B/C 仅是初始 AI 提示词中的逻辑分工，不代表多人共同完成本次提交。
- [ ] 若平台限制附件数量，可将 A/B/C 三组分别压缩；压缩包内仍保留原文件名和目录层次。

## 不需要作为本次实验 1 正式材料提交的文件

工程 Skeleton、后端/前端代码、Docker 运行日志、设计实验文档和 Git 同步说明不是本次“需求分析文档生成”作业的必需附件；除非教师另外要求，不以它们替代上表材料。
