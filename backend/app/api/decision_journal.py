"""决策日志与回溯 API — 记录决策预测，追踪实际结果。"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
