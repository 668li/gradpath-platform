# API Contract 001：/api/civil-service/timeline（FastAPI）

> **示例数据声明（09-12 立规）**：本文档内所有 JSON 示例的**日期/URL 一律为占位格式**（如 `<YYYY-MM-DD>`），不是数据、不得被实现或测试当作预期值；真实值唯一来源=spec §2.5 证据链（fetch 或 manual_paste）。测试断言日期一律"取 seed 写入值回读比对"，不硬编。

前缀 `/api/civil-service/timeline`（router 风格对齐现行 `prefix=/api/civil-service`）；鉴权沿用 `get_current_user`；响应 VO 显式声明 response_model（冒烟断言先读此文件）。错误语义：401=未登录、404、422=schema 不合、409=重复订阅。

## C1 GET /exams —— 考次列表（公开）
```jsonc
// 200
[{ "id":"uuid","code":"guokao-2027","name":"2027 国考","track":"guokao","year":2027,
   "status":"upcoming","official_home_url":"<gov 域官方入口>","next_node":{"stage_key":"announce","planned_date":"<YYYY-MM-DD>","date_status":"PREDICTED|UNKNOWN"} }]
```

## C2 GET /exams/{code} —— 考次详情+12 节点（公开）
```jsonc
// 200（节选，验证诚实字段全暴露）
{ "code":"guokao-2027","nodes":[
  { "stage_key":"announce","title":"公告发布","seq":1,"date_status":"PREDICTED",
    "planned_date":"<YYYY-MM-DD>","predict_basis":"按 2026 国考同环节已证实日期平移——该 2026 证据行不存在时本行不得为 PREDICTED，只能 UNKNOWN",
    "official_entry_url":"<官方报名入口 URL>","source_url":null,"collected_at":null,"evidence_id":null,
    "materials":["学历学位证明","报名照片"], "action_guide":"关注公告发布并核对职位表发布事件",
    "dark_knowledge":[{"id":"uuid","title":"…","confidence":"user"}] },
  { "stage_key":"registration","seq":2,"date_status":"UNKNOWN","planned_date":null,
    "predict_basis":null,"official_entry_url":"http://bm.scs.gov.cn/pp/gkweb/core/web/ui/business/home/gkhome.html", "…":null }
 ]}
// 404：code 不存在
```
**契约级负断言**：`date_status=UNKNOWN ⇒ planned_date==null && predict_basis==null`（响应模型校验，防前端猜日期）。

## C3 POST /exams/{code}/subscribe（登录）→ 201；重复 → 409
## C4 DELETE /exams/{code}/subscription（登录，软退订：置 notify_channels=[]，保留反馈史）→ 204
## C5 GET /me（登录）—— 我的订阅+各考"下一节点"高亮位+完成度
```jsonc
[{ "exam":{…C1 形},"progress":{"reached":4,"done":2,"feedback_rate":0.5},
   "next_node":{"stage_key":"written","planned_date":"<YYYY-MM-DD>","date_status":"OFFICIAL","is_predictive":false} }]
```

## C6 PUT /nodes/{node_id}/feedback（登录，须已订阅）
```jsonc
// req  { "status": "done" }         // done|uncertain|skipped
// 200  { "node_id":"uuid","status":"done","feedback_at":"…" }
// 404 未订阅该考/节点不属于订阅考 → 404（防跨考写回）
```

## C7 GET /nodes/{node_id}（公开）—— 单节点卡深链（分享/通知落地页用）

## 提醒产物（非 HTTP 契约，但定义"出口格式"）
- 站内：`Notification(type=reminder, title, content, link=/civil-service?tab=timeline&node=…)`
- Server 酱：title=节点行动句；正文含官方直链；**tone 断言/试探由 pick_template 闸决定，测试穿透见 FR3/data-model**。
- 幂等：撞 unique(user,node,kind) 静默跳过（无 409，job 内部语义）。

## 兼容与版本
本期新增不改动既有端点；`/api/gwy-positions` 处置见另一挂账（下线/外链提示），两者无耦合。
