# backend/app/services/retro_ai_service.py
"""AI 阶段复盘草稿服务层 — 基于 STAR 结构化事件调用 LLM 生成复盘草稿。

与 retrospective_service.generate_draft（规则版）互补，本服务调用 LLM
生成更丰富的结构化复盘内容，但不持久化（由调用方决定是否保存为 Retrospective）。
"""

import json
import re
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.services.ai_orchestrator import AIOrchestrator

SYSTEM_PROMPT = """你是一位资深的职业复盘教练，擅长引导用户回顾一段时间内的职业经历，提炼成就、挑战与经验教训。

你的任务：基于用户在指定时间段内的职业事件（含 STAR 结构化细节），生成一份阶段复盘草稿。

请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "achievements": ["成就1", "成就2", "..."],
  "challenges": "该时段面临的主要挑战（一段话）",
  "lessons_learned": "从经历中提炼的经验教训（一段话）",
  "next_steps": ["下一步行动1", "下一步行动2", "..."],
  "suggested_satisfaction": 1到5的整数，表示建议的满意度评分,
  "summary": "一段总结性回顾（200字以内）"
}

注意事项：
- achievements 至少给 1 条
- next_steps 至少给 2 条具体可执行的行动
- suggested_satisfaction 为 1-5 的整数
- 所有内容使用中文
- 结合提供的 STAR 细节，避免泛泛而谈"""


def _build_context(db: Session, user_id: UUID, period_start: date, period_end: date) -> str:
    """查询指定时段内的职业事件并格式化为文本，含 STAR 细节。"""
    events = (
        db.query(CareerEvent)
        .filter(
            CareerEvent.user_id == user_id,
            CareerEvent.event_date >= period_start,
            CareerEvent.event_date <= period_end,
        )
        .order_by(CareerEvent.event_date.desc())
        .all()
    )

    lines = [f"【复盘时段】{period_start} 至 {period_end}"]
    lines.append("【职业事件】")
    if events:
        for ev in events:
            lines.append(f"- {ev.event_date} [{ev.event_type.value}] {ev.title}")
            if ev.description:
                lines.append(f"  描述：{ev.description}")
            # STAR 细节（仅当事件具备时输出）
            if ev.situation or ev.task or ev.action or ev.result:
                if ev.situation:
                    lines.append(f"  Situation：{ev.situation}")
                if ev.task:
                    lines.append(f"  Task：{ev.task}")
                if ev.action:
                    lines.append(f"  Action：{ev.action}")
                if ev.result:
                    lines.append(f"  Result：{ev.result}")
    else:
        lines.append("（暂无记录）")

    return "\n".join(lines)


def _parse_llm_json(content: str) -> dict:
    """解析 LLM 返回的 JSON，支持容错。

    1. 尝试直接 json.loads
    2. 失败则用正则提取 ```json...``` 代码块
    3. 再失败则提取第一个 {...} 块
    4. 最终兜底返回默认结构
    """
    # 1. 直接解析
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. 提取 markdown 代码块
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # 3. 兜底：提取第一个 {...} 块
    brace_match = re.search(r"\{.*\}", content, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    # 4. 返回默认结构
    return {
        "achievements": [],
        "challenges": "",
        "lessons_learned": "",
        "next_steps": [],
        "suggested_satisfaction": 3,
        "summary": content,
    }


def _coerce_draft(data: dict) -> dict:
    """将解析后的 dict 强制转换为标准草稿结构，容忍字段缺失/类型错误。"""

    def _get_list(key: str) -> list:
        v = data.get(key, [])
        if not isinstance(v, list):
            return []
        return [str(x) for x in v]

    def _get_int(key: str, default: int = 3, lo: int = 1, hi: int = 5) -> int:
        v = data.get(key, default)
        try:
            iv = int(v)
        except (TypeError, ValueError):
            iv = default
        return max(lo, min(hi, iv))

    return {
        "achievements": _get_list("achievements"),
        "challenges": str(data.get("challenges", "")),
        "lessons_learned": str(data.get("lessons_learned", "")),
        "next_steps": _get_list("next_steps"),
        "suggested_satisfaction": _get_int("suggested_satisfaction", 3, 1, 5),
        "summary": str(data.get("summary", "")),
    }


async def generate_ai_retro_draft(
    db: Session, user_id: UUID, period_start: date, period_end: date
) -> dict:
    """生成 AI 复盘草稿：组装 context、调用 LLM、解析返回。

    与规则版 generate_draft 不同，本函数调用 LLM 生成结构化复盘内容，
    但不保存到数据库（由调用方决定是否持久化）。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        period_start: 复盘时段开始
        period_end: 复盘时段结束

    Returns:
        草稿数据 dict（achievements, challenges, lessons_learned, next_steps,
        suggested_satisfaction, summary）

    Raises:
        AIServiceNotConfigured: LLM_API_KEY 未配置（由 AIService._check_config 抛出）
    """
    # 组装 context（含 STAR 细节）
    context_text = _build_context(db, user_id, period_start, period_end)

    # 调用 LLM（AIOrchestrator 会在 key 为空时抛出 AIServiceNotConfigured）
    orchestrator = AIOrchestrator()
    user_content = (
        f"{context_text}\n\n" "请基于以上职业事件生成该时段的阶段复盘草稿（严格按 JSON 格式输出）。"
    )
    raw = await orchestrator.chat(system_prompt=SYSTEM_PROMPT, user_prompt=user_content, timeout=30)

    # 解析返回（不保存到 DB）
    data = _parse_llm_json(raw)
    return _coerce_draft(data)


# ======================================================================
# AI 引导式反思（2026-09-25 复盘深化）— 教练模式：一次只问一个维度
# ======================================================================

REFLECT_SYSTEM_PROMPT = """你是一位受过 AAR（After Action Review）训练的复盘教练，正在引导一位中国大学生做个人复盘。

流程遵循业界四段式共识（美军 AAR / 联想四步法 / KPT 同构）：
1. 还原事实：当时目标是什么、实际发生了什么（只摆差异，不评判）
2. 分析原因：为什么会有差异（先情绪后归因；区分可控/不可控）
3. 提炼规律：从这次经历能提炼出什么可复用的经验
4. 下次怎么办：如果再遇到同类情况，具体做什么不同的（此段最重要，占一半精力）

对话纪律（review-skill 六条规则的本土化）：
- 每轮只问一个问题，问完就停，等用户回答
- 能用选择题就不用开放题，但永远留"以上都不是"的自定义空间（在问题里说明可以直接打字）
- 用户情绪强烈时，先接住情绪再进分析（"听起来这件事让你很难受"），不跳过
- 适度魔鬼代言人：用户的归因太顺滑时，温和地质疑一次（"有没有可能还有另一个原因"）
- 双我思维：在第 3 段之后，替用户说出"最尖锐的一条反驳"（如果我是旁观者，我会怎么挑这次复盘的毛病）
- 全程中文，语气平等像学长学姐，不说教不端着

你每轮严格输出以下 JSON（不要输出 JSON 之外的任何内容，不要 markdown 代码块包裹）：
{
  "stage": "fact|analysis|insight|next_action|done",
  "question": "你的下一个问题（一个，具体，≤80字）",
  "options": ["选项A", "选项B", "选项C"],
  "acknowledge": "对用户上一条回答的简短回应（≤40字，接情绪或点出关键）",
  "sharp_rebuttal": "仅在第3段完成后输出：最尖锐的一条反驳（其他阶段为空字符串）"
}
"""


async def guide_reflection(messages: list[dict[str, str]], context_summary: str | None) -> dict:
    """AI 教练引导反思：输入历史对话，返回下一问。

    messages: [{role: "user"|"coach", content: "..."}]（前端持有完整历史）
    context_summary: replay 事实摘要（节点回传/事件/条件缺口的浓缩，可空）
    返回 {stage, question, options, acknowledge, sharp_rebuttal}
    """
    convo = ""
    for m in messages[-16:]:  # 上下文截断防 token 爆炸
        role = "教练" if m.get("role") != "user" else "用户"
        convo += f"{role}：{m.get('content', '')}\n"

    user_content = ""
    if context_summary:
        user_content += f"【该用户的站内事实记录（复盘时段）】\n{context_summary}\n\n"
    user_content += f"【对话历史】\n{convo or '（刚开始，请抛出第一个问题）'}\n\n"
    user_content += "请按对话纪律输出下一轮 JSON。"

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(
        system_prompt=REFLECT_SYSTEM_PROMPT, user_prompt=user_content, timeout=30
    )
    data = _parse_llm_json(raw)
    # 容错归一
    stage = data.get("stage", "fact")
    if stage not in {"fact", "analysis", "insight", "next_action", "done"}:
        stage = "fact"
    options = [str(o) for o in data.get("options", []) if o][:4]
    return {
        "stage": stage,
        "question": str(data.get("question", ""))[:200],
        "options": options,
        "acknowledge": str(data.get("acknowledge", ""))[:100],
        "sharp_rebuttal": str(data.get("sharp_rebuttal", ""))[:200],
    }


# ======================================================================
# AI 原则提炼 — 空话闸版（006 FR3）
# ======================================================================

PRINCIPLE_DRAFT_PROMPT = """你是一位经验萃取教练。任务：从用户的复盘中提炼可复用的个人原则。

原则条目铁律（NASA 经验教训库 + Ray Dalio 原则写法共识）：
- 触发条件必须具体到情境："当____的时候"，不许写"任何时候"
- 行动指令必须可执行：具体动作，不许写"要更努力/要坚持/要认真"这类空话
- 每条不超过 3 条（KPT：六条 Try 意味着一条也得不到关注）
- 优先提炼"下次再遇到同类情况怎么办"，而不是总结感受

严格输出 JSON（不要输出 JSON 之外的任何内容，不要 markdown 代码块包裹）：
{
  "principles": [
    {
      "trigger_scene": "当____的时候（≤60字，具体情境）",
      "action": "我应该____（≤80字，具体动作）",
      "rationale": "因为____（≤60字，可选，填空字符串则省略）",
      "scene_tags": ["标签1", "标签2"]
    }
  ]
}
scene_tags 从这些里选或自拟（≤2个）：模考崩盘/择校纠结/面试复盘/时间管理/状态中断/家庭沟通/出分落差/选岗/复试调剂/实习求职
"""


async def draft_principles(retro_content: str, replay_summary: str | None = None) -> list[dict]:
    """从复盘内容提炼 if-then 原则草稿（≤3 条）。空话闸在 service 层二次拦截。"""
    user_content = "【用户的复盘内容】\n" + retro_content[:4000]
    if replay_summary:
        user_content += "\n\n【站内事实记录摘要】\n" + replay_summary[:1500]
    user_content += "\n\n请提炼原则草稿（严格按 JSON 输出）。"

    orchestrator = AIOrchestrator()
    raw = await orchestrator.chat(
        system_prompt=PRINCIPLE_DRAFT_PROMPT, user_prompt=user_content, timeout=30
    )
    data = _parse_llm_json(raw)
    items = data.get("principles", [])
    if not isinstance(items, list):
        return []
    out = []
    for it in items[:3]:
        if not isinstance(it, dict):
            continue
        trigger = str(it.get("trigger_scene", "")).strip()
        action = str(it.get("action", "")).strip()
        if not trigger or not action:
            continue
        out.append(
            {
                "trigger_scene": trigger[:200],
                "action": action[:400],
                "rationale": str(it.get("rationale", "")).strip()[:500] or None,
                "scene_tags": [str(t).strip() for t in it.get("scene_tags", []) if str(t).strip()][
                    :3
                ],
            }
        )
    return out
