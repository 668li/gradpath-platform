"""暗知识主动推送服务 — 暗知识护城河。

将 1020 条暗知识从"被动检索"改为"主动推送"：
基于用户阶段、当前决策、历史阅读，主动推送最相关的暗知识。

推送策略（按优先级）：
1. 决策触发：用户创建决策时，推送该方向相关的高优先级暗知识
2. 阶段触发：根据用户当前阶段，推送该阶段未读的高优先级暗知识
3. 定时触发：每日推送 1-2 条新暗知识

去重：一条暗知识对同一用户最多推送一次。
"""
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.dark_knowledge_push import DarkKnowledgePushLog, PushFeedback
from app.models.grad_intel import DarkKnowledge

logger = logging.getLogger(__name__)

# 方向 → 阶段映射
_DIRECTION_TO_STAGE = {
    "postgrad": "decision",
    "employment": "decision",
    "civil_service": "decision",
    "abroad": "decision",
    "phd": "decision",
    "startup": "decision",
    "gap_year": "decision",
}

# 阶段优先级（数字越小优先级越高）
_STAGE_PRIORITY = {
    "decision": 1,
    "school_selection": 2,
    "preparation": 3,
    "exam": 4,
    "retest": 5,
    "transfer": 6,
}


def push_for_user(
    db: Session,
    user_id: UUID,
    stage: str | None = None,
    limit: int = 5,
    trigger: str = "manual",
    decision_id: UUID | None = None,
) -> list[DarkKnowledgePushLog]:
    """为用户推送暗知识。

    Args:
        stage: 用户当前阶段（None 则自动推断）
        limit: 最多推送条数
        trigger: 推送触发原因（manual / decision_created / daily / onboarding_completed）
        decision_id: 关联决策 ID（决策触发时）

    Returns:
        新创建的推送日志列表
    """
    # 1. 查询用户已推送过的暗知识 ID（去重）
    pushed_ids_subq = (
        db.query(DarkKnowledgePushLog.dark_knowledge_id)
        .filter(DarkKnowledgePushLog.user_id == user_id)
        .subquery()
    )
    pushed_ids = {row[0] for row in db.query(pushed_ids_subq).all()}

    # 2. 查询候选暗知识
    query = db.query(DarkKnowledge).filter(~DarkKnowledge.id.in_(pushed_ids)) if pushed_ids \
        else db.query(DarkKnowledge)

    # 按阶段过滤（如果有）
    if stage:
        query = query.filter(DarkKnowledge.stage == stage)

    # 按重要性 + 排序顺序排序
    candidates = (
        query.order_by(DarkKnowledge.importance.desc(), DarkKnowledge.sort_order.asc())
        .limit(limit * 3)  # 多取一些备用
        .all()
    )

    if not candidates:
        logger.info("无候选暗知识可推送 user_id=%s stage=%s", user_id, stage)
        return []

    # 3. 创建推送日志
    push_reason: dict[str, Any] = {"trigger": trigger}
    if decision_id:
        push_reason["decision_id"] = str(decision_id)
    if stage:
        push_reason["stage"] = stage

    created: list[DarkKnowledgePushLog] = []
    for dk in candidates[:limit]:
        log = DarkKnowledgePushLog(
            user_id=user_id,
            dark_knowledge_id=dk.id,
            stage=dk.stage,
            push_reason=push_reason,
        )
        db.add(log)
        created.append(log)

    if created:
        db.commit()
        for log in created:
            db.refresh(log)
        logger.info(
            "推送 %d 条暗知识给 user_id=%s trigger=%s stage=%s",
            len(created), user_id, trigger, stage,
        )

    return created


def push_for_decision(
    db: Session,
    user_id: UUID,
    decision_id: UUID,
    destination_type: str,
    limit: int = 3,
) -> list[DarkKnowledgePushLog]:
    """决策创建时触发的暗知识推送。"""
    stage = _DIRECTION_TO_STAGE.get(destination_type, "decision")
    return push_for_user(
        db=db,
        user_id=user_id,
        stage=stage,
        limit=limit,
        trigger="decision_created",
        decision_id=decision_id,
    )


def push_daily(db: Session, user_id: UUID, stage: str | None = None) -> list[DarkKnowledgePushLog]:
    """每日定时推送（最多 2 条）。"""
    return push_for_user(
        db=db,
        user_id=user_id,
        stage=stage,
        limit=2,
        trigger="daily",
    )


def mark_read(db: Session, user_id: UUID, push_id: UUID) -> DarkKnowledgePushLog | None:
    """标记推送为已读。"""
    log = (
        db.query(DarkKnowledgePushLog)
        .filter(
            DarkKnowledgePushLog.id == push_id,
            DarkKnowledgePushLog.user_id == user_id,
        )
        .first()
    )
    if not log:
        return None
    if log.read_at is None:
        log.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(log)
    return log


def record_feedback(
    db: Session,
    user_id: UUID,
    push_id: UUID,
    feedback: PushFeedback,
    rating: int | None = None,
    notes: str | None = None,
) -> DarkKnowledgePushLog | None:
    """记录用户对推送的反馈。"""
    log = (
        db.query(DarkKnowledgePushLog)
        .filter(
            DarkKnowledgePushLog.id == push_id,
            DarkKnowledgePushLog.user_id == user_id,
        )
        .first()
    )
    if not log:
        return None

    log.feedback = feedback
    if rating is not None:
        log.rating = max(1, min(5, rating))
    if notes:
        log.feedback_notes = notes[:500]  # 限制长度
    if log.read_at is None:
        log.read_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(log)
    return log


def get_push_history(
    db: Session,
    user_id: UUID,
    limit: int = 50,
    only_unread: bool = False,
) -> list[DarkKnowledgePushLog]:
    """查询用户推送历史。"""
    query = db.query(DarkKnowledgePushLog).filter(DarkKnowledgePushLog.user_id == user_id)
    if only_unread:
        query = query.filter(DarkKnowledgePushLog.read_at.is_(None))
    return (
        query.order_by(DarkKnowledgePushLog.pushed_at.desc())
        .limit(limit)
        .all()
    )


def get_unread_count(db: Session, user_id: UUID) -> int:
    """未读推送数。"""
    return (
        db.query(DarkKnowledgePushLog)
        .filter(
            DarkKnowledgePushLog.user_id == user_id,
            DarkKnowledgePushLog.read_at.is_(None),
        )
        .count()
    )
