"""用户上下文聚合服务 — 决策副驾驶核心数据底座。

聚合用户全维度数据（画像 + 诊断 + 记忆 + 决策 + 上岸报告），
为 AI 个性化提供统一上下文，避免每个 AI 端点重复查询。

设计：
- get_user_context: 返回结构化 dict，供 API 序列化
- build_context_prompt: 返回纯文本，供 AI system prompt 注入
"""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.assessment import Assessment
from app.models.career_profile import CareerProfile
from app.models.decision_review import DecisionReviewQueue, ReviewStatus
from app.models.destination_decision import DestinationDecision
from app.models.onboarding import UserOnboarding
from app.models.outcome_report import OutcomeReport
from app.models.user_memory import UserMemoryFact

logger = logging.getLogger(__name__)

# 完整版测评（主画像槽候选）与短版（学习风格信号槽）的契约划分。
# 新增测评类型时必须归入其一，并与前端 AssessmentType 联合类型对账
# （对账闸见 tests/test_assessment_contract.py）。
MAIN_ASSESSMENT_TYPES = ("holland", "mbti", "big_five", "disc")
LEARNING_STYLE_ASSESSMENT_TYPE = "big_five_short"


def get_user_context(db: Session, user_id: UUID) -> dict[str, Any]:
    """聚合用户上下文 — 用于 AI 个性化。

    Returns:
        {
            "career_profile": {...} | None,
            "onboarding": {...} | None,
            "memory_facts": [...],
            "recent_decisions": [...],
            "recent_outcome_reports": [...],
            "stats": {...},
        }
    """
    try:
        profile = db.query(CareerProfile).filter(CareerProfile.user_id == user_id).first()

        onboarding = (
            db.query(UserOnboarding)
            .filter(UserOnboarding.user_id == user_id)
            .order_by(UserOnboarding.created_at.desc())
            .first()
        )

        memory_facts = (
            db.query(UserMemoryFact)
            .filter(
                UserMemoryFact.user_id == user_id,
                UserMemoryFact.is_active.is_(True),
            )
            .order_by(UserMemoryFact.confidence.desc(), UserMemoryFact.use_count.desc())
            .limit(10)
            .all()
        )

        recent_decisions = (
            db.query(DestinationDecision)
            .filter(DestinationDecision.user_id == user_id)
            .order_by(DestinationDecision.created_at.desc())
            .limit(5)
            .all()
        )

        recent_reports = (
            db.query(OutcomeReport)
            .filter(OutcomeReport.user_id == user_id)
            .order_by(OutcomeReport.created_at.desc())
            .limit(3)
            .all()
        )

        # 主画像槽只认完整版测评；短版（big_five_short，低分辨率）单独成槽作
        # 学习风格信号——否则用户先做霍兰德再做短版，短版会把主画像顶掉
        # （2026-09-05 对抗审查 Spec 轴实锤）。
        latest_assessment = (
            db.query(Assessment)
            .filter(
                Assessment.user_id == user_id,
                Assessment.assessment_type.in_(MAIN_ASSESSMENT_TYPES),
            )
            .order_by(Assessment.created_at.desc())
            .first()
        )
        learning_style_assessment = (
            db.query(Assessment)
            .filter(
                Assessment.user_id == user_id,
                Assessment.assessment_type == LEARNING_STYLE_ASSESSMENT_TYPE,
            )
            .order_by(Assessment.created_at.desc())
            .first()
        )

        stats = _compute_stats(db, user_id)

        return {
            "career_profile": _serialize_profile(profile) if profile else None,
            "onboarding": _serialize_onboarding(onboarding) if onboarding else None,
            "memory_facts": [_serialize_memory_fact(f) for f in memory_facts],
            "recent_decisions": [_serialize_decision(d) for d in recent_decisions],
            "recent_outcome_reports": [_serialize_report(r) for r in recent_reports],
            "latest_assessment": (
                _serialize_assessment(latest_assessment) if latest_assessment else None
            ),
            "learning_style_assessment": (
                _serialize_assessment(learning_style_assessment)
                if learning_style_assessment
                else None
            ),
            "stats": stats,
        }
    except Exception as e:
        logger.exception("聚合用户上下文失败 user_id=%s: %s", user_id, e)
        return {
            "career_profile": None,
            "onboarding": None,
            "memory_facts": [],
            "recent_decisions": [],
            "recent_outcome_reports": [],
            "latest_assessment": None,
            "learning_style_assessment": None,
            "stats": {},
            "error": "context_unavailable",
        }


def _compute_stats(db: Session, user_id: UUID) -> dict[str, Any]:
    """计算用户决策副驾驶核心统计指标。"""
    total_decisions = (
        db.query(DestinationDecision).filter(DestinationDecision.user_id == user_id).count()
    )
    completed_reviews = (
        db.query(DecisionReviewQueue)
        .filter(
            DecisionReviewQueue.user_id == user_id,
            DecisionReviewQueue.status == ReviewStatus.completed,
        )
        .count()
    )
    pending_reviews = (
        db.query(DecisionReviewQueue)
        .filter(
            DecisionReviewQueue.user_id == user_id,
            DecisionReviewQueue.status.in_([ReviewStatus.pending, ReviewStatus.notified]),
        )
        .count()
    )
    memory_count = (
        db.query(UserMemoryFact)
        .filter(
            UserMemoryFact.user_id == user_id,
            UserMemoryFact.is_active.is_(True),
        )
        .count()
    )

    reviewed = (
        db.query(DecisionReviewQueue)
        .filter(
            DecisionReviewQueue.user_id == user_id,
            DecisionReviewQueue.status == ReviewStatus.completed,
        )
        .all()
    )
    accuracy_scores = [
        r.ai_review_result.get("accuracy_score", 0)
        for r in reviewed
        if r.ai_review_result and "accuracy_score" in r.ai_review_result
    ]
    avg_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.0

    return {
        "total_decisions": total_decisions,
        "completed_reviews": completed_reviews,
        "pending_reviews": pending_reviews,
        "memory_count": memory_count,
        "avg_decision_accuracy": round(avg_accuracy, 1),
    }


def _serialize_profile(p: CareerProfile) -> dict:
    return {
        "education_level": p.education_level,
        "major": p.major,
        "school_name": p.school_name,
        "school_tier": p.school_tier,
        "graduation_year": p.graduation_year,
        "target_direction": p.target_direction,
        "target_industry": p.target_industry,
        "technical_skill": p.technical_skill,
        "communication_skill": p.communication_skill,
        "leadership_skill": p.leadership_skill,
        "creativity_skill": p.creativity_skill,
        "self_introduction": p.self_introduction,
    }


def _serialize_onboarding(o: UserOnboarding) -> dict:
    return {
        "current_stage": o.current_stage,
        "target_direction": o.target_direction,
        "target_industry": o.target_industry,
        "ai_diagnosis": o.ai_diagnosis,
        "recommended_path": o.recommended_path,
        "key_insights": o.key_insights,
        "completed_at": o.completed_at.isoformat() if o.completed_at else None,
    }


def _serialize_memory_fact(f: UserMemoryFact) -> dict:
    return {
        "id": str(f.id),
        "fact_type": f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type),
        "fact_key": f.fact_key,
        "fact_value": f.fact_value,
        "confidence": f.confidence,
    }


def _serialize_decision(d: DestinationDecision) -> dict:
    return {
        "id": str(d.id),
        "destination_type": (
            d.destination_type.value
            if hasattr(d.destination_type, "value")
            else str(d.destination_type)
        ),
        "status": d.status.value if hasattr(d.status, "value") else str(d.status),
        "decision_date": d.decision_date.isoformat() if d.decision_date else None,
        "confidence": d.confidence,
        "prediction": d.prediction,
        "review_date": d.review_date.isoformat() if d.review_date else None,
        "review_completed": d.review_completed,
    }


def _serialize_report(r: OutcomeReport) -> dict:
    return {
        "id": str(r.id),
        "outcome_type": (
            r.outcome_type.value if hasattr(r.outcome_type, "value") else str(r.outcome_type)
        ),
        "target_school": r.target_school,
        "actual_school": r.actual_school,
        "satisfaction_after": r.satisfaction_after,
        "is_public": r.is_public,
    }


def _serialize_assessment(a: Assessment) -> dict:
    """测评摘要 — 为 AI 上下文提供职业兴趣倾向。"""
    return {
        "type": a.assessment_type,
        "result_code": a.result_code,
        "result_summary": a.result_summary,
        "recommended_directions": a.recommended_directions or [],
        "scores": a.scores or {},
    }


def build_context_prompt(db: Session, user_id: UUID) -> str:
    """构建用户上下文 prompt 文本 — 用于注入 AI system prompt。

    输出为纯文本，便于 LLM 理解。包含画像、诊断、记忆、决策、统计五部分。
    """
    ctx = get_user_context(db, user_id)

    if ctx.get("error"):
        return "（暂无用户上下文）"

    parts: list[str] = []

    if ctx["career_profile"]:
        p = ctx["career_profile"]
        parts.append(
            f"【用户画像】{p.get('education_level') or ''} {p.get('major') or ''} "
            f"来自 {p.get('school_name') or '未知学校'} "
            f"({p.get('school_tier') or ''}), "
            f"{p.get('graduation_year') or ''} 届毕业。"
            f"目标方向: {p.get('target_direction') or '未知'}, "
            f"目标行业: {p.get('target_industry') or '未知'}。"
        )
        skills = []
        for s in ["technical_skill", "communication_skill", "leadership_skill", "creativity_skill"]:
            v = p.get(s)
            if v is not None:
                skills.append(f"{s.replace('_skill', '')}={v}/5")
        if skills:
            parts.append("技能评分: " + ", ".join(skills) + "。")

    if ctx["onboarding"] and ctx["onboarding"].get("ai_diagnosis"):
        parts.append(f"【AI 诊断】{ctx['onboarding']['ai_diagnosis']}")

    if ctx["latest_assessment"]:
        a = ctx["latest_assessment"]
        lines = [f"【职业测评】类型：{a['type']}，编码：{a['result_code'] or '无'}"]
        if a.get("result_summary"):
            lines.append(a["result_summary"])
        if a.get("recommended_directions"):
            lines.append(f"推荐方向：{'、'.join(a['recommended_directions'])}")
        parts.append("；".join(lines))

    if ctx.get("learning_style_assessment"):
        ls = ctx["learning_style_assessment"]
        parts.append(
            f"【学习风格信号】大五短版 {ls.get('result_code') or ''}"
            "（每维 2 题，低分辨率参考，用于调整建议的节奏与方式，不作能力判断）"
        )

    if ctx["memory_facts"]:
        facts_str = "; ".join(
            f"{f['fact_key']}={f['fact_value']}(置信度{f['confidence']})"
            for f in ctx["memory_facts"]
        )
        parts.append(f"【已知事实】{facts_str}")

    if ctx["recent_decisions"]:
        decisions_str = "; ".join(
            f"{d['destination_type']}({d['status']}, 置信度{d['confidence']}/5)"
            for d in ctx["recent_decisions"]
        )
        parts.append(f"【最近决策】{decisions_str}")

    s = ctx["stats"]
    if s:
        parts.append(
            f"【统计】共 {s.get('total_decisions', 0)} 个决策, "
            f"完成回顾 {s.get('completed_reviews', 0)} 个, "
            f"待回顾 {s.get('pending_reviews', 0)} 个, "
            f"决策准确率 {s.get('avg_decision_accuracy', 0)}%, "
            f"AI 记忆 {s.get('memory_count', 0)} 条。"
        )

    return "\n".join(parts) if parts else "（暂无用户上下文）"
