import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.exceptions import NotFoundError
from app.models.destination_decision import DestinationDecision
from app.models.decision_review import DecisionReviewQueue, ReviewStatus
from app.schemas.decision import DecisionCreate, DecisionUpdate

logger = logging.getLogger(__name__)


def _invalidate_user_context_cache(user_id: UUID) -> None:
    """决策 CRUD 后失效用户上下文缓存（build_user_context 依赖 DestinationDecision）。"""
    try:
        cache.delete(f"user_context:{user_id}")
    except Exception:
        pass


def create_decision(db: Session, user_id: UUID, data: DecisionCreate) -> DestinationDecision:
    decision = DestinationDecision(user_id=user_id, **data.model_dump())
    db.add(decision)
    db.commit()
    db.refresh(decision)

    # 决策飞轮护城河：自动创建回顾任务（基于 review_date）
    _schedule_review_task(db, user_id, decision)

    # 暗知识护城河：决策创建时主动推送相关暗知识
    _trigger_dark_knowledge_push(db, user_id, decision)

    _invalidate_user_context_cache(user_id)
    return decision


def _schedule_review_task(db: Session, user_id: UUID, decision: DestinationDecision) -> None:
    """基于决策的 review_date 自动创建回顾任务（决策飞轮护城河）。"""
    if not decision.review_date:
        return
    try:
        # 检查是否已存在回顾任务（避免重复）
        existing = (
            db.query(DecisionReviewQueue)
            .filter(DecisionReviewQueue.decision_id == decision.id)
            .first()
        )
        if existing:
            return

        review = DecisionReviewQueue(
            user_id=user_id,
            decision_id=decision.id,
            scheduled_at=decision.review_date,
            status=ReviewStatus.pending,
        )
        db.add(review)
        db.commit()
        logger.info("已为决策 %s 创建回顾任务 scheduled_at=%s", decision.id, decision.review_date)
    except Exception as e:
        logger.warning("创建回顾任务失败 decision_id=%s: %s", decision.id, e)
        db.rollback()


def _trigger_dark_knowledge_push(db: Session, user_id: UUID, decision: DestinationDecision) -> None:
    """决策创建时主动推送相关暗知识（暗知识护城河）。"""
    try:
        from app.services.dark_knowledge_push_service import push_for_decision
        destination_type = (
            decision.destination_type.value
            if hasattr(decision.destination_type, "value")
            else str(decision.destination_type)
        )
        push_for_decision(db, user_id, decision.id, destination_type, limit=3)
    except Exception as e:
        logger.warning("触发暗知识推送失败 decision_id=%s: %s", decision.id, e)
        db.rollback()


def list_decisions(db: Session, user_id: UUID) -> list[DestinationDecision]:
    return (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .all()
    )


def list_decisions_paginated(
    db: Session, user_id: UUID, page: int = 1, page_size: int = 20
) -> tuple[list[DestinationDecision], int]:
    """分页查询去向决策列表（按决策日期降序）。"""
    query = db.query(DestinationDecision).filter(DestinationDecision.user_id == user_id)
    total = query.count()
    items = (
        query.order_by(DestinationDecision.decision_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_decision(db: Session, user_id: UUID, decision_id: UUID) -> DestinationDecision:
    decision = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.id == decision_id, DestinationDecision.user_id == user_id)
        .first()
    )
    if not decision:
        raise NotFoundError("决策记录不存在")
    return decision


def update_decision(db: Session, user_id: UUID, decision_id: UUID, data: DecisionUpdate) -> DestinationDecision:
    decision = get_decision(db, user_id, decision_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(decision, key, value)
    db.commit()
    db.refresh(decision)
    _invalidate_user_context_cache(user_id)
    return decision


def delete_decision(db: Session, user_id: UUID, decision_id: UUID) -> None:
    decision = get_decision(db, user_id, decision_id)
    db.delete(decision)
    db.commit()
    _invalidate_user_context_cache(user_id)


def get_decision_stats(db: Session, user_id: UUID) -> dict[str, int]:
    decisions = db.query(DestinationDecision).filter(DestinationDecision.user_id == user_id).all()
    stats: dict[str, int] = {}
    for d in decisions:
        key = d.destination_type.value
        stats[key] = stats.get(key, 0) + 1
    return stats
