# Data Model 001：时间线伴随

## 实体关系（ASCII）

```
Exam 1───* ExamNode(12, stage_key 枚举)
  │              │
  *              *
ExamSubscription 1───* NodeFeedback
  │(user)            │
 Users         TimelineReminderLog(user,node,kind 唯一)
```

## Exam（t_exam）

| 字段 | 类型 | 约束/说明 |
|---|---|---|
| id | UUID | PK，UUIDMixin |
| code | String(50) | unique，如 `guokao-2027`、`guokao-2026`、`guangdong-shengkao-2026` |
| name | String(100) | "2027 国考" |
| track | Enum | `guokao/shengkao/buwei_shengkao…`（枚举可扩展；考公先行） |
| year | Integer | 考次年份 |
| official_home_url | String(500) | 官方入口（有源必填） |
| status | Enum | `upcoming/ongoing/closed`（closed=周期走完，仍可浏览） |
| created/updated | TimestampMixin | |

**校验**：code 全局唯一；`official_home_url` 域名须过官方域名单校验（复用信任锚域名判定思路，M1 简单白名单即可）。

## ExamNode（t_exam_node）

| 字段 | 类型 | 约束 |
|---|---|---|
| exam_id | FK t_exam | index |
| stage_key | Enum(12) | announce/registration/payment/admission_ticket/written/score/adjustment/interview/medical/political/publicity/hire；(exam_id, stage_key) unique |
| node_seq | SmallInt | 1..12 |
| title | String(100) | "网上报名" |
| date_status | Enum | **OFFICIAL / PREDICTED / UNKNOWN**（默认 UNKNOWN） |
| planned_date | Date NULL | OFFICIAL/PREDICTED 必填，UNKNOWN 必空 |
| planned_end_date | Date NULL | 窗口型节点（报名起止/缴费截止）用 |
| predict_basis | String(200) NULL | 仅 PREDICTED：推算依据文本 |
| official_entry_url | String(500) NULL | 官方入口直链 |
| source_url | String(500) NULL | **date_status=OFFICIAL 时必填** |
| collected_at | DateTime(tz) NULL | 同上必填（采集时间） |
| evidence_id | FK t_timeline_evidence NULL | **OFFICIAL 时必填**（FR-E1 闸校验）；UNKNOWN/PREDICTED 必空 |
| materials | JSON | 材料清单 [{name, note?}] |
| action_guide | Text | "该做什么"摘要（人工撰写，非生成） |
| announced_via_announce_id | UUID NULL | Phase 2 回填位（FR10），本期恒 NULL |

## TimelineEvidence（t_timeline_evidence）—— 证据链实体（09-12 新增）

| 字段 | 约束 |
|---|---|
| id | UUID PK |
| channel | Enum `fetch / manual_paste` |
| source_url | String(500) 必填，域名须在政府域白名单（*.gov.cn） |
| fetched_at | DateTime(tz) 必填（fetch=请求时刻；manual_paste=粘贴入库时刻） |
| content_sha | String(64) fetch=响应体 sha256；manual_paste=粘贴文本 sha256 |
| matched_excerpt | Text 必填，命中日期的正文片段（含日期串±60 字） |
| pasted_text | Text NULL，manual_paste 全量原文留档 |
| recorded_by | String(100)（user email/`seed_fetch:<job_id>`，审计到人） |

**写路径唯一**：`require_evidence(url, date_value)`——fetch：真发 HTTP→200→正文≥2KB→归一化含 `date_value`→才允许产 evidence 行；manual_paste：粘贴文本含 `date_value` 才放行。**seed/API/service 一律经此函数，禁旁路**。OFFICIAL 行创建/转换时若 evidence_id 缺失或证据 channel 与来源不符 → 写入拒绝（服务层+DB 双约束 NOT NULL 组合校验）。

**状态机/转换**：`UNKNOWN→PREDICTED`（seed 推算写入）；`{UNKNOWN,PREDICTED}→OFFICIAL`（官方捕获覆写，predict_basis 清空、source_url/collected_at 必填）；`OFFICIAL→OFFICIAL`（官方更正重采）；**禁止 `OFFICIAL→PREDICTED/UNKNOWN`**（回退=数据质量事故，人工走 seed 变更）。
**负例闸**：任何写路径校验 source_url 非空 ⇒ 仅当 OFFICIAL 或预测依据字段存在；闸函数 `validate_honesty(node)` 单点，服务层统一调用。**预测锚点链（spec FR-E6）**：`PREDICTED` ⇒ `predict_basis` 必须引用同系列上一年同一 `stage_key` 且其 `evidence_id` 非空的行；链断则只许 `UNKNOWN`——推算的推算还是编造。

## ExamSubscription（t_exam_subscription）

| 字段 | 约束 |
|---|---|
| user_id, exam_id | **unique(user,exam)** |
| notify_channels | JSON，默认 ["inapp","serverchan"]，可按用户关（退订≠删除，保留回传史） |
| created | |

## NodeFeedback（t_exam_node_feedback）

| 字段 | 约束 |
|---|---|
| subscription_id, node_id | unique(sub,node)；node_id ∈ 该订阅 exam |
| status | Enum `done/uncertain/skipped`（不建"未完成"负值——未回传即缺行） |
| feedback_at | DateTime |

北极星：`条件完成率 = done 节点数 / 已到达提醒窗口节点数`；`回传率 = 有反馈行的提醒数 / 发出提醒数`（定义同步进 docs/度量口径.md）。

## TimelineReminderLog（t_timeline_reminder_log）

| 字段 | 约束 |
|---|---|
| user_id, node_id, kind | **unique(user,node,kind)** = 幂等硬闸（D4） |
| kind | Enum `heads_up/opening/deadline_t1/dayof/followup`（映射 D5 提前量表） |
| tone | Enum `assertive/tentative`（落库供审计，验证闸生效） |
| sent_at, channel, notification_id | |

**校验**：写入前经 `pick_template()`（D2 单点闸）；测试断言 tone==assertive ⇒ 关联 node.date_status==OFFICIAL，穿到渲染字符串层（FR3）。

## 关系与删除策略

Exam 不物理删（status=closed 即归档）；节点随 seed upsert；Subscription 级联保留（退订软删）。所有表沿用 UUIDMixin+TimestampMixin+Base 现行基类。
