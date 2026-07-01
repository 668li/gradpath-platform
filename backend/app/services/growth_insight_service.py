# backend/app/services/growth_insight_service.py
"""AI 成长洞察服务层 — 基于用户一段时间内的职业事件、技能、决策、复盘，
调用 LLM 生成结构化成长分析，并按 event_count 缓存结果。

缓存策略：相同 user_id + period_start + period_end + event_count 时直接返回
已缓存的 insight_data，避免重复调用 LLM。
"""
import json
import re
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.destination_decision import DestinationDecision
from app.models.growth_insight import GrowthInsight
from app.models.retrospective import Retrospective
from app.models.skill_node import SkillNode
from app.services.ai_service import AIService

# Context 中各类数据的条数上限（事件取最近 50 条）
EVENT_LIMIT = 50
SKILL_LIMIT = 20
DECISION_LIMIT = 10
RETRO_LIMIT = 10

SYSTEM_PROMPT = """你是一位资深的职业成长教练，擅长基于个人职业轨迹数据给出成长洞察分析。

你的任务：基于用户在指定时间段内的职业事件、技能树、历史决策与阶段复盘数据，分析用户的成长状态，并给出结构化的成长洞察。

请严格输出以下 JSON 结构（不要输出任何 JSON 之外的内容，不要使用 markdown 代码块包裹）：

{
  "growth_score": 0到100的整数，表示该时段的综合成长得分,
  "trend": "rising" 或 "stable" 或 "declining",
  "strengths": ["优势1", "优势2", "..."],
  "gaps": ["能力短板1", "能力短板2", "..."],
  "recommendations": ["建议1", "建议2", "..."],
  "summary": "一段总结性评价（200字以内）"
}

注意事项：
- growth_score 为 0-100 的整数
- trend 只能是 rising / stable / declining 三者之一
- strengths 和 gaps 至少各给 1 条
- recommendations 至少给 2 条具体可执行建议
- 所有内容使用中文
- 分析要结合用户提供的数据，避免泛泛而谈"""


def _build_context(
    db: Session,
    user_id: UUID,
    period_start: date,
    period_end: date,
) -> tuple[str, int]:
    """查询指定时段内的职业事件、技能、决策、复盘并格式化为文本。

    Returns:
        (context_text, event_count) — context 文本与该时段事件总数
        （event_count 为完整计数，用于缓存校验）
    """
    lines = [f"【分析时段】{period_start} 至 {period_end}"]

    # 职业事件（取最近 50 条用于 context 组装）
    events = (
        db.query(CareerEvent)
        .filter(
            CareerEvent.user_id == user_id,
            CareerEvent.event_date >= period_start,
            CareerEvent.event_date <= period_end,
        )
        .order_by(CareerEvent.event_date.desc())
        .limit(EVENT_LIMIT)
        .all()
    )
    # 完整事件计数（用于缓存校验，不受 limit 影响）
    event_count = (
        db.query(CareerEvent)
        .filter(
            CareerEvent.user_id == user_id,
            CareerEvent.event_date >= period_start,
            CareerEvent.event_date <= period_end,
        )
        .count()
    )
    lines.append("【职业事件】")
    if events:
        for ev in events:
            lines.append(f"- {ev.event_date} [{ev.event_type.value}] {ev.title}")
    else:
        lines.append("（暂无记录）")

    # 技能（按 level 降序）
    skills = (
        db.query(SkillNode)
        .filter(SkillNode.user_id == user_id)
        .order_by(SkillNode.level.desc())
        .limit(SKILL_LIMIT)
        .all()
    )
    lines.append("【技能树】")
    if skills:
        for s in skills:
            lines.append(f"- {s.name}(Lv{s.level}) 分类:{s.category}")
    else:
        lines.append("（暂无记录）")

    # 历史决策（时段内）
    decisions = (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.user_id == user_id,
            DestinationDecision.decision_date >= period_start,
            DestinationDecision.decision_date <= period_end,
        )
        .order_by(DestinationDecision.decision_date.desc())
        .limit(DECISION_LIMIT)
        .all()
    )
    lines.append("【历史决策】")
    if decisions:
        for d in decisions:
            lines.append(
                f"- {d.decision_date} [{d.destination_type.value}] "
                f"状态={d.status.value} 置信度={d.confidence}"
            )
    else:
        lines.append("（暂无记录）")

    # 阶段复盘（与时段有交集的复盘）
    retros = (
        db.query(Retrospective)
        .filter(
            Retrospective.user_id == user_id,
            Retrospective.period_end >= period_start,
            Retrospective.period_start <= period_end,
        )
        .order_by(Retrospective.period_end.desc())
        .limit(RETRO_LIMIT)
        .all()
    )
    lines.append("【阶段复盘】")
    if retros:
        for r in retros:
            lines.append(
                f"- {r.title}({r.period_start}~{r.period_end}) "
                f"满意度={r.satisfaction}"
            )
    else:
        lines.append("（暂无记录）")

    return "\n".join(lines), event_count


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
        "growth_score": 50,
        "trend": "stable",
        "strengths": [],
        "gaps": [],
        "recommendations": [],
        "summary": content,
    }


def _coerce_insight(data: dict) -> dict:
    """将解析后的 dict 强制转换为标准洞察结构，容忍字段缺失/类型错误。"""

    def _get_list(key: str) -> list:
        v = data.get(key, [])
        if not isinstance(v, list):
            return []
        return [str(x) for x in v]

    def _get_int(key: str, default: int = 50, lo: int = 0, hi: int = 100) -> int:
        v = data.get(key, default)
        try:
            iv = int(v)
        except (TypeError, ValueError):
            iv = default
        return max(lo, min(hi, iv))

    trend = str(data.get("trend", "stable"))
    if trend not in ("rising", "stable", "declining"):
        trend = "stable"

    return {
        "growth_score": _get_int("growth_score", 50, 0, 100),
        "trend": trend,
        "strengths": _get_list("strengths"),
        "gaps": _get_list("gaps"),
        "recommendations": _get_list("recommendations"),
        "summary": str(data.get("summary", "")),
    }


def generate_growth_insight(
    db: Session, user_id: UUID, period_start: date, period_end: date
) -> dict:
    """生成成长洞察：组装 context、检查缓存、调用 LLM、解析并保存。

    Args:
        db: 数据库会话
        user_id: 用户 ID
        period_start: 分析时段开始
        period_end: 分析时段结束

    Returns:
        洞察数据 dict（growth_score, trend, strengths, gaps, recommendations, summary）

    Raises:
        AIServiceNotConfigured: LLM_API_KEY 未配置（由 AIService._check_config 抛出）
    """
    # 组装 context 并获取完整事件计数
    context_text, event_count = _build_context(
        db, user_id, period_start, period_end
    )

    # 检查缓存：相同 user_id + period_start + period_end + event_count
    cached = (
        db.query(GrowthInsight)
        .filter(
            GrowthInsight.user_id == user_id,
            GrowthInsight.period_start == period_start,
            GrowthInsight.period_end == period_end,
            GrowthInsight.event_count == event_count,
        )
        .order_by(GrowthInsight.generated_at.desc())
        .first()
    )
    if cached:
        return cached.insight_data

    # 调用 LLM（AIService._check_config 会在 key 为空时抛出 AIServiceNotConfigured）
    service = AIService()
    user_content = (
        f"{context_text}\n\n"
        "请基于以上数据生成该时段的成长洞察（严格按 JSON 格式输出）。"
    )
    raw = service.chat(SYSTEM_PROMPT, user_content, timeout=30)

    # 解析返回
    data = _parse_llm_json(raw)
    insight_data = _coerce_insight(data)

    # 保存到 DB
    insight = GrowthInsight(
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        insight_data=insight_data,
        event_count=event_count,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(insight)
    db.commit()

    return insight_data


def get_latest_insight(db: Session, user_id: UUID) -> dict | None:
    """返回用户最近一次成长洞察数据，无则返回 None。"""
    latest = (
        db.query(GrowthInsight)
        .filter(GrowthInsight.user_id == user_id)
        .order_by(GrowthInsight.generated_at.desc())
        .first()
    )
    if latest:
        return latest.insight_data
    return None
