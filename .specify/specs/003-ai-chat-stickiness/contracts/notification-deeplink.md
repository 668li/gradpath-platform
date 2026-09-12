# Contract：节点提醒深链（build_chat_deep_link）

## 唯一生成函数

```python
# backend/app/services/chat_deep_link.py
def build_chat_deep_link(node: ExamNode, exam: Exam, tone: ReminderTone) -> str:
    """所有提醒→对话深链的唯一出口；禁止他处手拼（spec FR4）。"""
```

## URL 形态

```
/chat?prefill=<urlencode(文案)>&skill=timeline_companion&src=reminder&node=<node_id>
```

| 参数 | 规则 |
|---|---|
| prefill | 一句话节点上下文文案，**tone 分级**：OFFICIAL ⇒ 直陈式（"明天就是 {node.title} 截止…"）；tentative/PREDICTED ⇒ 试探式（"预计近期 {node.title}，我帮你盯官方公告…"）。措辞模板内聚本函数，与 `timeline_reminder.ASSERTIVE_WORDS` 禁词表同源校验；**>100 字截断**（Notification.link String(500) 容量硬闸） |
| skill | 固定 `timeline_companion`（对话页预选该 skill，与 skillHint state 对齐） |
| src | 固定 `reminder`（点击归因口径，FR8） |
| node | 节点 UUID hex（回传钩子据此锚定同一节点） |

## 消费点（全部走此函数，禁止手拼）

| 消费点 | 现状 | 变更 |
|---|---|---|
| `timeline_reminder.pick_template` 的 `ReminderDraft.link` | 现为 `/civil-service?tab=timeline&node={id}`（timeline_reminder.py:139） | 改为 `build_chat_deep_link(node, exam, tone)` |
| `_send_one` 站内 `push_notification(link=…)` | 已落 Notification.link | 随 ReminderDraft.link 自动切换 |
| `_send_one` Server酱 content | 仅 title+content，无 URL（timeline_reminder.py:235） | content 尾部追加一行：`进对话页直接问：{settings.SITE_BASE_URL}{link}` |

## 时间诚实负例（宪法 4，测试断言打到最终产物）

1. `date_status=PREDICTED` 的节点 ⇒ 解码 prefill 文案**不得命中** `ASSERTIVE_WORDS` 任一禁词。
2. `date_status=OFFICIAL` 节点 ⇒ prefill 可用直陈式。
3. Server酱 content 含完整绝对 URL（`SITE_BASE_URL` 前缀）且同 tone 规则。
4. prefill >100 字 ⇒ 截断且 URL 总长 ≤500 字符。

## 保留语义

`/civil-service?tab=timeline&node=` 路径**不废弃**：回传钩子（contracts/chat-api.md feedback_node）仍指向它；时间线 tab 的节点定位语义不变。
