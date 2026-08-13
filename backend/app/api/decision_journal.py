"""决策日志与回溯 API — 记录决策预测，追踪实际结果。"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.destination_decision import DestinationDecision
from app.models.user import User
from app.schemas.decision import DecisionResponse
from app.schemas.decision_journal import DecisionReviewSubmit
from app.services import decision_journal_service

router = APIRouter(prefix="/api/decision-journal", tags=["决策日志与回溯"])


@router.get("/pending-reviews", response_model=list[DecisionResponse])
def get_pending_reviews(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取待回溯的决策列表（已到回溯日期但未完成回溯）。"""
    decisions = decision_journal_service.get_pending_reviews(db, user.id)
    return [DecisionResponse.model_validate(d) for d in decisions]


@router.get("/reviewed", response_model=list[DecisionResponse])
def get_reviewed_decisions(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取已完成回溯的决策列表。"""
    decisions = decision_journal_service.get_reviewed_decisions(db, user.id)
    return [DecisionResponse.model_validate(d) for d in decisions]


@router.post("/{decision_id}/review", response_model=DecisionResponse)
async def complete_review(
    decision_id: UUID,
    body: DecisionReviewSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """完成决策回溯评估，填写实际结果。"""
    # 修复 bug: service 层 raise ValueError("决策不存在或无权访问") -> 500，应转 404
    try:
        decision = await decision_journal_service.complete_review(
            db, user.id, decision_id, body.actual_outcome, body.review_notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return DecisionResponse.model_validate(decision)


# ======================================================================
# 决策时间胶囊 — 写给未来自己的信，回溯时拆开
# ======================================================================

class TimeCapsuleWrite(BaseModel):
    letter: str = Field(..., min_length=1, max_length=2000, description="写给未来自己的信")


def _get_owned_decision(db: Session, user_id: UUID, decision_id: UUID) -> DestinationDecision:
    """获取属于当前用户的决策，否则 404。"""
    decision = (
        db.query(DestinationDecision)
        .filter(
            DestinationDecision.id == decision_id,
            DestinationDecision.user_id == user_id,
        )
        .first()
    )
    if not decision:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="决策不存在")
    return decision


@router.post("/{decision_id}/time-capsule")
def seal_time_capsule(
    decision_id: UUID,
    body: TimeCapsuleWrite,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """封存时间胶囊：决策时写一封信给未来的自己。"""
    decision = _get_owned_decision(db, user.id, decision_id)
    details = dict(decision.details or {})
    details["time_capsule"] = {
        "letter": body.letter.strip(),
        "sealed_at": date.today().isoformat(),
        "opened": False,
    }
    decision.details = details
    db.commit()
    db.refresh(decision)
    return {"sealed": True, "sealed_at": details["time_capsule"]["sealed_at"]}


@router.get("/{decision_id}/time-capsule")
def open_time_capsule(
    decision_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """拆开时间胶囊：仅在到达回溯日期或已完成回溯后可读。"""
    decision = _get_owned_decision(db, user.id, decision_id)
    capsule = (decision.details or {}).get("time_capsule")
    if not capsule:
        return {"has_capsule": False, "can_open": False, "letter": None}

    # 回溯日期已到 或 已完成回溯，才允许拆封
    today = date.today()
    reached_review = decision.review_completed or (
        decision.review_date is not None and decision.review_date <= today
    )
    if not reached_review:
        return {
            "has_capsule": True,
            "can_open": False,
            "letter": None,
            "sealed_at": capsule.get("sealed_at"),
            "opens_on": decision.review_date.isoformat() if decision.review_date else None,
            "message": "这封信要等到回溯那天才能拆开 — 给未来的自己一点时间",
        }

    # 标记已拆封
    if not capsule.get("opened"):
        details = dict(decision.details or {})
        details["time_capsule"]["opened"] = True
        decision.details = details
        db.commit()

    return {
        "has_capsule": True,
        "can_open": True,
        "letter": capsule.get("letter"),
        "sealed_at": capsule.get("sealed_at"),
        "opened": True,
    }
