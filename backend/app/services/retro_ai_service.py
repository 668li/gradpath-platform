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
from app.services.ai_service import AIService

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


def _build_context(
    db: Session, user_id: UUID, period_start: date, period_end: date
) -> str:
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


def generate_ai_retro_draft(
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

    # 调用 LLM（AIService._check_config 会在 key 为空时抛出 AIServiceNotConfigured）
    service = AIService()
    user_content = (
        f"{context_text}\n\n"
        "请基于以上职业事件生成该时段的阶段复盘草稿（严格按 JSON 格式输出）。"
    )
    raw = service.chat(SYSTEM_PROMPT, user_content, timeout=30)

    # 解析返回（不保存到 DB）
    data = _parse_llm_json(raw)
    return _coerce_draft(data)
