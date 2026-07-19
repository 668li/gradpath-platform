# backend/app/services/ai_butler_service.py
"""AI 管家统一服务 — 单一功能「扫描我的数据 + 给出方案」。

设计目标（第一性原理）：
- AI 管家不应散落在 7 个页面当补丁，而是「扫描用户全量数据 → 结构化画像 → 行动清单」。
- 生产环境 LLM_API_KEY 可能为空，因此画像与方案必须有「纯 DB + 启发式」降级路径。
- LLM 仅在 key 存在时做润色/补充，绝不阻塞主流程。

对外暴露：
- scan_user(user_id) -> {profile, plan, generated_at, llm_enriched}
- route_agent(user_id, message, web_search, conversation_id) -> AgentResponse 风格字典
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.assessment import Assessment
from app.models.bookmark import Bookmark
from app.models.career_plan import CareerPlan
from app.models.destination_decision import DestinationDecision
from app.models.experience_post import ExperiencePost
from app.models.proactive_insight import ProactiveInsight
from app.models.qa import QA
from app.models.retrospective import Retrospective
from app.models.skill_node import SkillNode
from app.models.user import User
from app.services.chat_service import build_user_context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 数据聚合
# ---------------------------------------------------------------------------

def _count(db: Session, model, user_id: UUID, **filters) -> int:
    stmt = select(func.count()).select_from(model).where(model.user_id == user_id)
    for k, v in filters.items():
        stmt = stmt.where(getattr(model, k) == v)
    return db.scalar(stmt) or 0


def _build_profile(db: Session, user_id: UUID) -> dict:
    """聚合用户全量信号，产出结构化画像。"""
    user = db.get(User, user_id)
    profile: dict[str, Any] = {
        "identity": {
            "name": user.name if user else "未知用户",
            "stage": user.current_stage.value if (user and user.current_stage) else None,
            "school": user.school if (user and user.school) else None,
            "major": user.major if (user and user.major) else None,
            "graduation_year": user.graduation_year if (user and user.graduation_year) else None,
        },
        "inventory": {
            "decisions": _count(db, DestinationDecision, user_id),
            "events": _count(db, _CareerEvent, user_id),
            "skills": _count(db, SkillNode, user_id),
            "retrospectives": _count(db, Retrospective, user_id),
            "career_plans": _count(db, CareerPlan, user_id),
            "assessments": _count(db, Assessment, user_id),
            "bookmarks": _count(db, Bookmark, user_id),
            "insights": _count(db, ProactiveInsight, user_id),
            "experience_posts": _count(db, ExperiencePost, user_id),
            "qa_asked": _count(db, QA, user_id),
        },
        "active_plans": _active_plan_summary(db, user_id),
        "latest_assessment": _latest_assessment_summary(db, user_id),
        "gaps": _infer_gaps(db, user_id),
    }
    return profile


def _build_action_plan(profile: dict) -> list[dict]:
    """基于画像启发式生成行动清单。每条含 priority/title/why/action。"""
    plan: list[dict] = []
    inv = profile["inventory"]
    gaps = profile["gaps"]

    if inv["assessments"] == 0:
        plan.append({
            "priority": "high",
            "title": "完成职业测评",
            "why": "尚无霍兰德测评，无法标定方向",
            "action": "前往「职业规划 → 测评」完成霍兰德评估，获取推荐方向。",
        })
    if inv["decisions"] == 0:
        plan.append({
            "priority": "high",
            "title": "做出第一个去向决策",
            "why": "尚未记录任何考研/考公/就业决策",
            "action": "在「决策实验室」记录你的目标去向并评估置信度。",
        })
    if inv["career_plans"] == 0:
        plan.append({
            "priority": "medium",
            "title": "创建一份职业规划",
            "why": "有决策但无落地路径",
            "action": "基于决策创建含里程碑的规划，设定时间线。",
        })
    elif not profile["active_plans"]:
        plan.append({
            "priority": "medium",
            "title": "推进停滞的规划",
            "why": "存在规划但无进行中状态",
            "action": "将一份规划置为 active 并标记已完成里程碑。",
        })
    if inv["skills"] == 0:
        plan.append({
            "priority": "medium",
            "title": "建立技能树",
            "why": "竞争力无法量化",
            "action": "在「技能」页登记你的核心技能与等级。",
        })
    if inv["retrospectives"] == 0 and inv["decisions"] > 0:
        plan.append({
            "priority": "low",
            "title": "做一次阶段复盘",
            "why": "有决策但从未复盘",
            "action": "在「复盘」页总结上一阶段并给出满意度。",
        })
    for g in gaps:
        plan.append({
            "priority": "medium",
            "title": f"补齐：{g}",
            "why": "画像数据缺失，影响 AI 判断精度",
            "action": f"在个人中心补充「{g}」信息。",
        })
    if not plan:
        plan.append({
            "priority": "low",
            "title": "保持节奏",
            "why": "数据较完整",
            "action": "维持打卡与复盘，AI 将基于历史给出更精准洞察。",
        })
    return plan


def _infer_gaps(db: Session, user_id: UUID) -> list[str]:
    gaps: list[str] = []
    user = db.get(User, user_id)
    if not user:
        return gaps
    if not user.current_stage:
        gaps.append("当前阶段")
    if not user.school:
        gaps.append("学校")
    if not user.major:
        gaps.append("专业")
    if not user.graduation_year:
        gaps.append("毕业年份")
    return gaps


def _active_plan_summary(db: Session, user_id: UUID) -> list[dict]:
    plans = (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id, CareerPlan.status == "active")
        .order_by(CareerPlan.created_at.desc())
        .limit(3)
        .all()
    )
    out = []
    for p in plans:
        total = len(p.milestones or [])
        done = sum(
            1 for m in (p.milestones or [])
            if isinstance(m, dict) and m.get("status") == "completed"
        )
        out.append({
            "goal": p.goal_text,
            "progress": f"{done}/{total}",
            "timeline_months": p.timeline_months,
        })
    return out


def _latest_assessment_summary(db: Session, user_id: UUID) -> dict | None:
    a = (
        db.query(Assessment)
        .filter(Assessment.user_id == user_id)
        .order_by(Assessment.created_at.desc())
        .first()
    )
    if not a:
        return None
    return {
        "type": a.assessment_type,
        "code": a.result_code,
        "summary": a.result_summary,
        "directions": a.recommended_directions,
    }


# ---------------------------------------------------------------------------
# 对外 API
# ---------------------------------------------------------------------------

def scan_user(db: Session, user_id: UUID) -> dict:
    """扫描用户全量数据，返回结构化画像 + 行动清单。

    LLM 仅做可选润色；key 缺失时纯 DB + 启发式合成，绝不报错。
    """
    profile = _build_profile(db, user_id)
    plan = _build_action_plan(profile)

    llm_enriched = False
    if getattr(settings, "LLM_API_KEY", None):
        try:
            profile, plan = _llm_enrich(profile, plan)
            llm_enriched = True
        except Exception as e:  # noqa: BLE001
            logger.warning("AI 管家 LLM 润色失败，回退启发式: %s", e)

    return {
        "profile": profile,
        "plan": plan,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm_enriched": llm_enriched,
        "context": build_user_context(db, user_id),
    }


def _llm_enrich(profile: dict, plan: list[dict]) -> tuple[dict, list[dict]]:
    """可选：用 LLM 把画像/方案润色成更自然的中文叙述。"""
    from app.services.ai_service import AIService

    ai = AIService()
    prompt = (
        "你是职业规划顾问。基于以下用户画像与行动清单，"
        "输出一段 200 字以内的鼓励性总结（不要新增事实）。\n"
        f"画像: {profile}\n方案: {plan}"
    )
    summary = ai.chat(
        "你只做总结润色，不编造数据。", prompt, timeout=20
    )
    profile = dict(profile)
    profile["summary"] = summary
    return profile, plan


def route_agent(
    db: Session,
    user_id: UUID,
    message: str,
    web_search: bool = True,
) -> dict:
    """将用户问题路由到 Agent（DB/Web 检索），并附带用户上下文。

    复用 ai_agent 的检索逻辑，但注入用户上下文，使回答个性化。
    返回与 AgentResponse 兼容的字典。
    """
    # 延迟导入避免循环依赖
    from app.api.ai_agent import _db_search, _classify_intent
    from app.services.web_search import WebSearchService

    intent = _classify_intent(message)
    db_results = _db_search(message, limit=5)
    web_results: list[dict] = []
    if web_search:
        try:
            web_results = [
                {"title": h.title, "content": h.snippet, "url": h.url}
                for h in WebSearchService().search(message, max_results=5)
            ]
        except Exception as e:  # noqa: BLE001
            logger.warning("Web search failed: %s", e)

    context = build_user_context(db, user_id)
    answer = _synthesize(message, intent, db_results, web_results, context)

    has_db = bool(db_results)
    has_web = bool(web_results)
    confidence = 0.9 if (has_db and has_web) else 0.7 if has_db else 0.6 if has_web else 0.3

    return {
        "answer": answer,
        "sources": [
            {"type": "db", "title": r["title"], "content": r["content"], "url": r["url"]}
            for r in db_results
        ] + [
            {"type": "web", "title": r["title"], "content": r["content"], "url": r["url"]}
            for r in web_results
        ],
        "confidence": confidence,
        "intent": intent,
    }


def _synthesize(
    message: str,
    intent: str,
    db_results: list[dict],
    web_results: list[dict],
    context: str,
) -> str:
    """纯 DB/启发式合成回答（LLM 缺失时的降级路径）。"""
    parts = [f"关于「{message}」（方向：{intent}）"]
    if db_results:
        parts.append("\n平台内相关资料：")
        for r in db_results[:5]:
            parts.append(f"- {r['title']}：{r['content'][:120]}")
    if web_results:
        parts.append("\n网络补充：")
        for r in web_results[:3]:
            parts.append(f"- {r['title']}：{r['content'][:120]}")
    if not db_results and not web_results:
        parts.append("\n暂未找到相关资料，建议换个关键词，或前往三大方向中心查看情报。")
    parts.append("\n（提示：可在 AI 管家页查看基于你全部数据的专属方案）")
    return "\n".join(parts)


# 延迟引用，避免模块加载期循环导入
from app.models.career_event import CareerEvent  # noqa: E402

_CareerEvent = CareerEvent
