"""暗知识主动推送 API — 暗知识护城河接口。

GET /api/dark-knowledge-push: 查询推送历史
GET /api/dark-knowledge-push/unread-count: 未读数
POST /api/dark-knowledge-push/push: 手动触发推送
POST /api/dark-knowledge-push/{push_id}/read: 标记已读
POST /api/dark-knowledge-push/{push_id}/feedback: 记录反馈
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.dark_knowledge_push import PushFeedback
from app.models.user import User
from app.services.dark_knowledge_push_service import (
    get_push_history,
    get_unread_count,
    mark_read,
    push_for_user,
    record_feedback,
)

router = APIRouter(prefix="/api/dark-knowledge-push", tags=["暗知识推送"])


class PushRequest(BaseModel):
    stage: str | None = Field(None, max_length=50, description="阶段")
    limit: int = Field(5, ge=1, le=20)


class FeedbackRequest(BaseModel):
    feedback: str = Field(..., max_length=20, description="positive / negative / later")
    rating: int | None = Field(None, ge=1, le=5)
    notes: str | None = Field(None, max_length=500)


def _serialize(log):
    return {
        "id": str(log.id),
        "user_id": str(log.user_id),
        "dark_knowledge_id": str(log.dark_knowledge_id),
        "stage": log.stage,
        "push_reason": log.push_reason,
        "pushed_at": log.pushed_at.isoformat() if log.pushed_at else None,
        "read_at": log.read_at.isoformat() if log.read_at else None,
        "is_read": log.read_at is not None,
        "feedback": log.feedback.value if hasattr(log.feedback, "value") else str(log.feedback),
        "feedback_notes": log.feedback_notes,
        "rating": log.rating,
    }


@router.get("")
def list_pushes(
    only_unread: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询推送历史。"""
    pushes = get_push_history(db, user.id, limit=limit, only_unread=only_unread)
    return {"items": [_serialize(p) for p in pushes], "total": len(pushes)}


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """未读推送数。"""
    return {"count": get_unread_count(db, user.id)}


@router.post("/push")
def trigger_push(
    req: PushRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动触发推送（用户主动获取新暗知识）。"""
    logs = push_for_user(
        db=db,
        user_id=user.id,
        stage=req.stage,
        limit=req.limit,
        trigger="manual",
    )
    return {"pushed_count": len(logs), "items": [_serialize(l) for l in logs]}


@router.post("/{push_id}/read")
def read(
    push_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记推送为已读。"""
    log = mark_read(db, user.id, push_id)
    if not log:
        raise HTTPException(status_code=404, detail="推送记录不存在")
    return _serialize(log)


@router.post("/{push_id}/feedback")
def feedback(
    push_id: UUID,
    req: FeedbackRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """记录推送反馈。"""
    try:
        fb = PushFeedback(req.feedback)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的 feedback 值")

    log = record_feedback(
        db=db,
        user_id=user.id,
        push_id=push_id,
        feedback=fb,
        rating=req.rating,
        notes=req.notes,
    )
    if not log:
        raise HTTPException(status_code=404, detail="推送记录不存在")
    return _serialize(log)
