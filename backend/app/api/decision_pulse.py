"""决策副驾驶看板 API — Dashboard 数据接口。

GET /api/decision-pulse: 完整看板数据（总览+决策+回顾+推送+记忆）
GET /api/decision-pulse/overview: 仅总览统计
GET /api/decision-pulse/active-decisions: 进行中决策
GET /api/decision-pulse/review-queue: 待回顾队列
GET /api/decision-pulse/dark-knowledge-feed: 暗知识推送流
GET /api/decision-pulse/memory-facts: AI 记忆面板
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.decision_pulse_service import (
    get_active_decisions,
    get_dark_knowledge_feed,
    get_full_pulse,
    get_memory_facts_panel,
    get_pulse_overview,
    get_review_queue,
)

router = APIRouter(prefix="/api/decision-pulse", tags=["决策副驾驶"])


@router.get("")
def full_pulse(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """完整看板数据（一次调用返回所有面板）。"""
    return get_full_pulse(db, user.id)


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """总览统计。"""
    return get_pulse_overview(db, user.id)


@router.get("/active-decisions")
def active_decisions(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """进行中决策列表。"""
    return {"items": get_active_decisions(db, user.id, limit=limit)}


@router.get("/review-queue")
def review_queue(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """待回顾决策队列。"""
    return {"items": get_review_queue(db, user.id, limit=limit)}


@router.get("/dark-knowledge-feed")
def dark_knowledge_feed(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """暗知识推送流。"""
    return {"items": get_dark_knowledge_feed(db, user.id, limit=limit)}


@router.get("/memory-facts")
def memory_facts(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 记忆面板。"""
    return {"items": get_memory_facts_panel(db, user.id, limit=limit)}
