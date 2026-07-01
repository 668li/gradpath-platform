# backend/app/api/career_plans.py
"""职业规划 API 路由 — Phase 11。

- GET /api/career-plans — 列出用户的规划
- GET /api/career-plans/{id} — 规划详情
- PATCH /api/career-plans/{id}/milestones/{idx} — 更新里程碑状态
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import CareerPlanResponse, MilestoneUpdate
from app.services.career_plan_service import get_plan, list_plans, update_milestone

router = APIRouter(prefix="/api/career-plans", tags=["职业规划"])


@router.get("", response_model=list[CareerPlanResponse])
def list_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出用户的规划。"""
    return list_plans(db, user.id)


@router.get("/{plan_id}", response_model=CareerPlanResponse)
def get_one(
    plan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取规划详情。"""
    plan = get_plan(db, user.id, plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规划不存在")
    return plan


@router.patch("/{plan_id}/milestones/{milestone_idx}", response_model=CareerPlanResponse)
def update_milestone_status(
    plan_id: UUID,
    milestone_idx: int,
    body: MilestoneUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新里程碑状态。"""
    plan = update_milestone(db, user.id, plan_id, milestone_idx, body.status)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规划或里程碑不存在")
    return plan
