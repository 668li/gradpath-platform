# Contracts 004：公告季事件 API

> 约定：路径前缀 `/api/v1`；浏览面公开（未登录可见，与 001 时间线一致）；写入面登录+admin。响应字段的 `source_url / fetched_at / credibility` 为宪法 1 的强制三件套，缺一不可渲染。

## C1 · 事件列表（公开）

```
GET /api/v1/kaogong/events?event_type=&since=&limit=&offset=
```

响应：

```json
{
  "items": [
    {
      "id": 1,
      "event_type": "posting_list",
      "title": "2027 国考职位表已发布",
      "url": "https://...",
      "detected_at": "2026-10-14T12:03:00+08:00",
      "lifecycle": "published",
      "credibility": "OFFICIAL",
      "evidence": {"source_url": "https://...", "fetched_at": "...", "excerpt": "..."}
    }
  ],
  "total": 1
}
```

- `event_type ∈ {announce, posting_list, interview_list, adjustment, supplement, publicity}`
- 未过 `verified` 的事件**不出现在公开响应**（待核验态只在 admin 面）

## C2 · 情报卡（公开）

```
GET /api/v1/kaogong/intel-cards?since=
```

```json
{
  "items": [
    {
      "id": 1,
      "event_id": 1,
      "title": "职位表已发布",
      "direct_url": "https://...",
      "credibility": "OFFICIAL",
      "created_at": "...",
      "event": {"title": "...", "detected_at": "..."}
    }
  ]
}
```

- 卡片不含职位内容字段（红线）

## C3 · manual_paste 证据录入（admin）

```
POST /api/v1/admin/evidence/manual-paste
Body: {"source_url": "https://官方域/...", "pasted_text": "公告全文...", "operator": "..."}
```

- 校验：`source_url` 属官方域 + `pasted_text` 含声明日期串 → 写 evidence（渠道=manual_paste，留粘贴人+时间+全文 sha）
- 通过 → 返回 `evidence_id`，供事件行挂载
- 失败 → 422（复用"422 报错体是最快权威源"的调试惯例）

## C4 · 时间线节点挂载（复用 001 契约扩展）

- `GET /api/v1/civil-service/timeline/...` 的节点对象增可空字段 `latest_event_ref`（含 `event_id/title/detected_at`）
- 不改 001 既有字段语义；无事件时字段缺省（负例：不得渲染空壳引用）

## C5 · SLA 度量（admin）

```
GET /api/v1/admin/metrics/announcement-sla?from=&to=
→ {"p50_hours": N, "p90_hours": N, "samples": N, "unusable": N}
```

- `unusable` = `published_hint` 为空（不参与均值），口径写入 `docs/度量口径.md` 增补节
