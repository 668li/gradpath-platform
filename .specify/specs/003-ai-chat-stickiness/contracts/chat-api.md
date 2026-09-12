# Contract：Chat API 变更（SendMessageResponse.action_hooks）

## 不变部分

`POST /api/chat/conversations/{conversation_id}/messages` 请求体不变：`{content, skill_hint?}`（schemas/chat.py:45-47）。既有响应字段语义不变。

## 响应新增可选字段

```jsonc
// SendMessageResponse（schemas/chat.py:50-57）追加：
{
  "content": "…AI 回答正文…",
  "skill_used": "timeline_companion",
  "career_plan": null,
  "micro_action_plan": null,
  "agent_sources": [ … ],
  "agent_confidence": 0.7,
  "action_hooks": [                      // 新增，可为 null（降级/无钩子）
    {
      "type": "subscribe_timeline",      // 钩子类型码，见下表
      "text": "帮你盯 国考2027 的时间线，节点准时提醒",  // ≤40 字，模板+库数据插值
      "link": "/civil-service?tab=timeline"  // 站内相对路径；探索型可为 null
    }
  ]
}
```

## 钩子类型码（type 枚举初版）

| type | 触发条件（查真实库） | link 目标 |
|---|---|---|
| subscribe_timeline | timeline/announcements 域，当前 exam 未订阅 | 考公中心考试流程 tab |
| feedback_node | timeline 域，存在已到达窗口且无 NodeFeedback 的节点 | `/civil-service?tab=timeline&node={id}` |
| micro_checkin | 存在 active 微行动计划 | 微行动页 |
| explore | 用户无任何沉淀时的探索型钩子 | 测评/微行动入口 |

## 语义约束（验收口径）

1. 每轮 ≤2 个（spec FR7）；按上表优先级截取。
2. "已做过"不重复推销：已订阅 ⇒ 无 subscribe_timeline；无待回传 ⇒ 无 feedback_node（spec FR2/FR3）。
3. 钩子服务任何异常 ⇒ `action_hooks=null`，回答正文不受影响（spec FR7 降级负例）。
4. 钩子文案为服务端模板常量+库数据插值，不含 LLM 生成内容；含日期的钩子过宪法 4 分级（PREDICTED 试探式）。
5. 前端渲染：胶囊按钮置于回答气泡尾部；点击 `router.push(link)`；曝光不额外上报（读 context_snapshot 口径）。

## 前端类型

`frontend/lib/api/` 中 SendMessageResponse 对应类型补 `action_hooks?: {type: string; text: string; link: string | null}[] | null`。
