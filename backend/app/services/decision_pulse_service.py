"""决策副驾驶看板服务 — 用户主面板数据聚合。

为 Dashboard 提供决策副驾驶看板所需的全部数据：
- 总览统计（决策数、准确率、记忆数、暗知识数）
- 进行中决策列表
- 待回顾决策队列
- 暗知识推送流
- AI 记忆事实面板
"""
import logging
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.dark_knowledge_push import DarkKnowledgePushLog, PushFeedback
from app.models.decision_review import DecisionReviewQueue, ReviewStatus
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.models.grad_intel import DarkKnowledge
from app.models.user_memory import UserMemoryFact
from app.services.user_context_service import _compute_stats

logger = logging.getLogger(__name__)


def get_pulse_overview(db: Session, user_id: UUID) -> dict[str, Any]:
    """决策副驾驶看板总览数据。"""
    stats = _compute_stats(db, user_id)

    # 待回顾决策数（已到期）
    today = date.today()
    due_reviews = (
        db.query(DecisionReviewQueue)
        .filter(
            DecisionReviewQueue.user_id == user_id,
            DecisionReviewQueue.status.in_([ReviewStatus.pending, ReviewStatus.notified]),
            DecisionReviewQueue.scheduled_at <= today,
        )
        .count()
    )

    # 未读暗知识数
    unread_pushes = (
        db.query(DarkKnowledgePushLog)
        .filter(
            DarkKnowledgePushLog.user_id == user_id,
            DarkKnowledgePushLog.read_at.is_(None),
        )
        .count()
    )

    # 进行中决策数
    active_decisions_count = (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.user_id == user_id,
            DestinationDecision.status.in_([DecisionStatus.planned, DecisionStatus.confirmed]),
        )
        .count()
    )

    return {
        **stats,
        "due_reviews": due_reviews,
        "unread_pushes": unread_pushes,
        "active_decisions": active_decisions_count,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


def get_active_decisions(db: Session, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
    """进行中决策列表（planned + confirmed）。"""
    decisions = (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.user_id == user_id,
            DestinationDecision.status.in_([DecisionStatus.planned, DecisionStatus.confirmed]),
        )
        .order_by(DestinationDecision.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(d.id),
            "destination_type": d.destination_type.value if hasattr(d.destination_type, "value") else str(d.destination_type),
            "status": d.status.value if hasattr(d.status, "value") else str(d.status),
            "decision_date": d.decision_date.isoformat() if d.decision_date else None,
            "confidence": d.confidence,
            "prediction": d.prediction,
            "review_date": d.review_date.isoformat() if d.review_date else None,
            "reasoning": d.reasoning[:200] + "..." if d.reasoning and len(d.reasoning) > 200 else d.reasoning,
        }
        for d in decisions
    ]


def get_review_queue(db: Session, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
    """待回顾决策队列。"""
    reviews = (
        db.query(DecisionReviewQueue)
        .filter(
            DecisionReviewQueue.user_id == user_id,
            DecisionReviewQueue.status.in_([ReviewStatus.pending, ReviewStatus.notified]),
        )
        .order_by(DecisionReviewQueue.scheduled_at.asc())
        .limit(limit)
        .all()
    )
    today = date.today()
    return [
        {
            "id": str(r.id),
            "decision_id": str(r.decision_id),
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "is_overdue": r.scheduled_at < today if r.scheduled_at else False,
            "days_until_due": (r.scheduled_at - today).days if r.scheduled_at else None,
        }
        for r in reviews
    ]


def get_dark_knowledge_feed(db: Session, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
    """暗知识推送流（最近推送 + 未读优先）。"""
    # 未读优先，其次按推送时间倒序
    pushes = (
        db.query(DarkKnowledgePushLog)
        .filter(DarkKnowledgePushLog.user_id == user_id)
        .order_by(
            DarkKnowledgePushLog.read_at.is_(None).desc(),  # 未读优先
            DarkKnowledgePushLog.pushed_at.desc(),
        )
        .limit(limit)
        .all()
    )

    # 关联查询 DarkKnowledge 内容
    result: list[dict[str, Any]] = []
    for p in pushes:
        dk = (
            db.query(DarkKnowledge)
            .filter(DarkKnowledge.id == p.dark_knowledge_id)
            .first()
        )
        result.append({
            "push_id": str(p.id),
            "dark_knowledge_id": str(p.dark_knowledge_id),
            "stage": p.stage,
            "pushed_at": p.pushed_at.isoformat() if p.pushed_at else None,
            "read_at": p.read_at.isoformat() if p.read_at else None,
            "is_read": p.read_at is not None,
            "feedback": p.feedback.value if hasattr(p.feedback, "value") else str(p.feedback),
            "title": dk.title if dk else "(已删除)",
            "category": dk.category if dk else "",
            "content": dk.content[:300] + "..." if dk and len(dk.content) > 300 else (dk.content if dk else ""),
            "importance": dk.importance if dk else "medium",
            "actionable_advice": dk.actionable_advice if dk else None,
        })
    return result


def get_memory_facts_panel(db: Session, user_id: UUID, limit: int = 20) -> list[dict[str, Any]]:
    """AI 记忆面板（最近 + 高置信度）。"""
    facts = (
        db.query(UserMemoryFact)
        .filter(
            UserMemoryFact.user_id == user_id,
            UserMemoryFact.is_active.is_(True),
        )
        .order_by(UserMemoryFact.created_at.desc(), UserMemoryFact.confidence.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(f.id),
            "fact_type": f.fact_type.value if hasattr(f.fact_type, "value") else str(f.fact_type),
            "fact_key": f.fact_key,
            "fact_value": f.fact_value,
            "confidence": f.confidence,
            "source": f.source,
            "use_count": f.use_count,
            "user_feedback": f.user_feedback,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in facts
    ]


def get_full_pulse(db: Session, user_id: UUID) -> dict[str, Any]:
    """获取完整看板数据（一次调用返回所有面板数据）。"""
    return {
        "overview": get_pulse_overview(db, user_id),
        "active_decisions": get_active_decisions(db, user_id),
        "review_queue": get_review_queue(db, user_id),
        "dark_knowledge_feed": get_dark_knowledge_feed(db, user_id),
        "memory_facts": get_memory_facts_panel(db, user_id),
    }
