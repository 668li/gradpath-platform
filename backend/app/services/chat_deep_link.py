# backend/app/services/chat_deep_link.py
"""节点提醒 → AI 对话页深链的唯一生成出口（speckit 003 FR4/FR6）。

所有"提醒侧 → 对话页"的链接必须经 build_chat_deep_link 产出，Server酱
文案追加链接行必须经 with_chat_link——禁止他处手拼。prefill 文案的
时间诚实分级（宪法 4）在本文件单点保证：

- tone=assertive（仅 OFFICIAL 节点）⇒ 直陈式措辞；
- tone=tentative（PREDICTED/UNKNOWN 降级后）⇒ 试探式措辞，措辞表与
  timeline_reminder.ASSERTIVE_WORDS 的禁词从构造上不相交（负例测试
  在 tests 层做交叉断言，本模块不 import timeline_reminder 防循环）。

容量硬闸：Notification.link 是 String(500)，prefill 超预算自动截断
（research R5/规格 data-model「容量核对」）。
"""

from __future__ import annotations

import logging
from urllib.parse import quote

from app.config import settings

logger = logging.getLogger(__name__)

# prefill 为一句话（URL 编码后极占长度：1 个汉字 ≈ 9 个百分号编码字符）
_PREFILL_MAX = 40  # 汉字上限，超出截断
_LINK_MAX = 500  # Notification.link String(500) 容量硬闸

_SKILL = "timeline_companion"
_SRC = "reminder"

# 试探式模板（tentative）——禁词表交叉校验见 tests/test_chat_stickiness_003.py
_TENTATIVE_TEMPLATES = {
    "heads_up": "「{exam}」的「{node}」预计近期有动静，我帮你盯官方公告",
    "opening": "「{exam}」的「{node}」预计近期开启，我帮你盯官方公告",
    "deadline_t1": "「{exam}」的「{node}」预计近期收尾，我帮你盯官方公告",
    "dayof": "「{exam}」的「{node}」预计近期进行，我帮你盯官方公告",
    "followup": "「{exam}」的「{node}」之后预计有后续安排，我帮你盯官方公告",
}
_FALLBACK_TENTATIVE = "「{exam}」的「{node}」预计近期有更新，我帮你盯官方公告"

# 直陈式模板（assertive，仅 OFFICIAL 可达此分支——tone 由 pick_template 单点闸判定）
_ASSERTIVE_TEMPLATES = {
    "heads_up": "「{exam}」的「{node}」临近了",
    "opening": "「{exam}」的「{node}」已经开启",
    "deadline_t1": "「{exam}」的「{node}」明天截止",
    "dayof": "今天就是「{exam}」的「{node}」",
    "followup": "「{exam}」的「{node}」已结束，聊聊后续安排",
}


def build_chat_deep_link(node, exam, kind, tone) -> str:
    """构造 /chat 深链：prefill 节点上下文 + 预选 timeline_companion。

    Args:
        node: ExamNode（取 title/id）
        exam: Exam（取 name）
        kind: ReminderKind（措辞按提醒语义选择）
        tone: ReminderTone（pick_template 的 D2 判定结果，本函数不重新判定）
    """
    kind_key = getattr(kind, "value", str(kind))
    tone_key = getattr(tone, "value", str(tone))
    templates = _ASSERTIVE_TEMPLATES if tone_key == "assertive" else _TENTATIVE_TEMPLATES
    template = templates.get(kind_key) or _TENTATIVE_TEMPLATES.get(kind_key) or _FALLBACK_TENTATIVE
    prefill = template.format(
        node=getattr(node, "title", "") or "该节点", exam=getattr(exam, "name", "") or "本场考试"
    )

    node_id = quote(str(getattr(node, "id", "")), safe="")
    tail = f"&skill={_SKILL}&src={_SRC}&node={node_id}"
    budget = _LINK_MAX - len("/chat?prefill=") - len(tail)
    prefill = prefill[:_PREFILL_MAX]
    encoded = quote(prefill, safe="")
    while len(encoded) > max(budget, 0) and prefill:
        prefill = prefill[:-1]
        encoded = quote(prefill, safe="")
    return f"/chat?prefill={encoded}{tail}"


def with_chat_link(content: str, link: str) -> str:
    """Server酱 desp 尾部追加对话页深链行；SITE_BASE_URL 未配置时原样返回。

    这是推送层对 ReminderDraft.content 唯一允许的追加（纯 URL 行，
    不触碰语义文案）；tone 合规性由上游 pick_template 与本模块模板保证。
    """
    base = (settings.SITE_BASE_URL or "").strip().rstrip("/")
    if not base or not link:
        return content
    return f"{content}\n\n进 GradPath 对话页直接问：{base}{link}"
