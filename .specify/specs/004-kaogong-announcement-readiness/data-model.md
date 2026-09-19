# Data Model 004：考公公告季监控

> 复用优先：事件归口 `official_announce`、信任锚 `_fetch_log`（002）、展示挂载 `ExamNode`（001）、通知 `Notification`（001）。新增仅三张表。

## 新增实体

### SourceWatch（监控源）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | PK | |
| name | str | 源名（如"国考-公告发布-转登页"） |
| url | str | 监控页 URL（仅官方域，红线校验落 yaml 纯函数） |
| domain_ok | bool | 域白名单校验结果（gov.cn / gd.gov.cn 等官方域；edu.cn 不在本 spec 范围） |
| event_type | enum | announce / posting_list / interview_list / adjustment / supplement / publicity |
| check_interval | str | 日常频率（日扫）｜窗口频率（升档配置） |
| fingerprint_sha | str | 最近一次正文 content_sha（diff 基准） |
| enabled | bool | 来源线开关（对应"人工抽查零缺报→默认不开"的砍线判据 H9） |
| last_checked_at | ts | |

### ExamEvent（事件）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | PK | |
| source_id | FK→SourceWatch | |
| event_type | enum | 同上（与源一致） |
| title | str | 事件标题（如"2027 国考公告已发布"） |
| url | str | 官方入口/原文 URL |
| evidence_id | FK→evidence | **必填**（FR-E1b：无证据不得展示） |
| detected_at | ts | 捕获时间（SLA 分子） |
| published_hint | ts? | 可见最早公开时间（SLA 分母，可空=不参与均值） |
| dedup_key | str | 幂等键：(source_id, event_type, 日期串/标题指纹) |
| lifecycle | enum | detected → verified → published（站内可见）→ stable/updated |

**状态流转**：detected（指纹命中）→ verified（证据闸过）→ published（展示面可见）；来源内容再变 → updated（原事件追加 diff 摘要，不新开行）。

### IntelCard（外链型情报卡）

| 字段 | 类型 | 说明 |
|---|---|---|
| id | PK | |
| event_id | FK→ExamEvent | |
| card_type | enum | external_link（本 spec 仅此一种） |
| title | str | 如"职位表已发布" |
| direct_url | str | 官方下载/查看直链 |
| credibility | enum | OFFICIAL / PREDICTED（沿用宪法 4 语义） |
| created_at | ts | |

**红线**：卡片**不含**职位内容字段（无岗位/条件/名额）；只承载"事件已发生+去哪里看"。

## 复用实体（不改结构）

| 实体 | 用途 | 出处 |
|---|---|---|
| official_announce | 事件同归口查询面 | 002 归口 |
| evidence（_fetch_log） | 证据行（source_url/fetched_at/content_sha/excerpt/渠道） | 002 信任锚 |
| ExamNode / ExamSubscription / NodeFeedback | 时间线节点引用事件（挂载展示，不改模型） | 001 |
| Notification | 订阅者站内通知（幂等/配额沿用） | 001 |

## 验证规则（落库前）

1. `event_type=announce` 且 `lifecycle≥verified` ⇒ evidence 非空且 `_fetch_log` 正文 ≥2KB（壳页拒收）。
2. 日期串必须出现在证据正文（归一化比对）；OFFICIAL 判定不复用模型记忆。
3. manual_paste 渠道：粘贴人+时间+全文留档；`credibility=OFFICIAL` 需粘贴文本含日期串校验通过。
4. 同一 dedup_key 重复入库=幂等忽略（不更新 detected_at 之外的字段）。