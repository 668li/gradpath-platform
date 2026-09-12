# Data Model 003：AI 对话粘性三件套

**零新增实体、零迁移。** 本 feature 全部复用现有表；以下记录读路径与两处现有结构的扩载（均为 JSON 可选字段，无 DDL）。

## 复用实体（只读）

| 实体 | 表 | 本 feature 消费方式 | 证据 |
|---|---|---|---|
| ExamSubscription | t_exam_subscription | 沉淀块：用户在订阅的考次（join Exam 取名称）；订阅钩子判定：timeline 域当前 exam 是否已订阅（unique(user_id, exam_id) 存在性） | models/exam_timeline.py:198 |
| NodeFeedback | t_exam_node_feedback | 沉淀块：最近回传记录；回传钩子判定：已到达窗口节点 ∩ 无 feedback 行（unique(subscription_id, node_id) 反查） | models/exam_timeline.py:219 |
| Exam / ExamNode | t_exam / t_exam_node | 沉淀块与深链文案的节点名/考次名/date_status（tone 判定输入） | models/exam_timeline.py:93 |
| MicroActionPlan / MicroActionTask | micro_action_plans / micro_action_tasks | 沉淀块：active 计划的 target_path/当前 day_number；打卡钩子判定：active 计划存在性 | models/micro_action.py:17,41 |
| StreakRecord | （models/streak.py） | 沉淀块：current_streak_days（连击天数） | reminder_service.py:23 引用先例 |
| Notification | notifications | **写路径仅 1 处改值**：`_send_one` 的 `link` 从 `/civil-service?tab=timeline&node=` 改为 chat 深链；字段结构零变更（String(500) 容量评估见下） | models/notification.py:34 |

## 现有结构扩载（无 DDL）

### Message.context_snapshot（JSONB，已有列）

新增可选键：

```json
{
  "action_hooks": [
    {"type": "subscribe_timeline", "text": "帮你盯 国考2027 的时间线，节点准时提醒", "link": "/civil-service?tab=timeline"}
  ]
}
```

- 写入点：chat_service.py:523-527 的 context_snapshot 组装处追加。
- 用途：钩子曝光口径（FR8）；点击口径走对话页 PV 的 `src=reminder&node=` 参数，不另立表。

### SendMessageResponse（Pydantic，已有 schema）

新增可选字段 `action_hooks: list[ActionHook] | None = None`；`ActionHook = {type: str, text: str, link: str | None}`。向后兼容（旧前端忽略未知字段）。契约细节见 [contracts/chat-api.md](./contracts/chat-api.md)。

## 新增配置（.env/settings，非数据库）

| 键 | 值（生产） | 用途 |
|---|---|---|
| SITE_BASE_URL | https://quxianglab.cn | Server酱文案内深链的绝对 URL 前缀（backend/app/core/config.py 新增 settings 项） |

## 容量/边界核对

- `Notification.link` String(500)：深链 = `/chat?prefill=<≤120字 urlencode ≈360B>&skill=timeline_companion&src=reminder&node=<32hex>` ≈ 500B 上限边缘 → `build_chat_deep_link` 内置 prefill 截断（>100 字截断加省略号），硬闸防溢出。
- 沉淀块每轮查询成本：4 组主键/索引查询（订阅 join exam、待回传反查、active 计划、streak），单轮 <10ms 量级；无缓存（新鲜度优先，见 research R1）。
- `TimelineReminderLog` 幂等键不变：unique(user, node, kind)（models/exam_timeline.py:239-241）——link 变更不影响幂等语义。
