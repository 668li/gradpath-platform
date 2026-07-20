# backend/app/api/career_plans.py
"""职业规划 API 路由 — Phase 11 / Phase 12。

- GET /api/career-plans — 列出用户的规划
- GET /api/career-plans/reminders — 到期提醒（Phase 12）
- GET /api/career-plans/daily-focus — 每日重点（Phase 12）
- GET /api/career-plans/{id} — 规划详情
- PATCH /api/career-plans/{id}/milestones/{idx} — 更新里程碑状态
- POST /api/career-plans/{id}/milestones/{idx}/logs — 添加执行日志（Phase 12）
- GET /api/career-plans/{id}/milestones/{idx}/logs — 列出执行日志（Phase 12）
- DELETE /api/career-plans/{id}/logs/{log_id} — 删除执行日志（Phase 12）
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.chat import (
    CareerPlanResponse,
    DailyFocusItem,
    MilestoneLogCreate,
    MilestoneLogResponse,
    MilestoneUpdate,
    ReminderItem,
)
from app.services.career_plan_service import (
    add_milestone_log,
    delete_milestone_log,
    get_daily_focus,
    get_plan,
    get_reminders,
    list_milestone_logs,
    list_plans,
    update_milestone,
)

router = APIRouter(prefix="/api/career-plans", tags=["职业规划"])


@router.get("", response_model=list[CareerPlanResponse])
def list_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出用户的规划。"""
    return list_plans(db, user.id)


@router.get("/reminders", response_model=list[ReminderItem])
def get_user_reminders(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """到期提醒：分类返回 overdue 与 upcoming 的里程碑。"""
    return get_reminders(db, user.id)


@router.get("/daily-focus", response_model=list[DailyFocusItem])
def get_user_daily_focus(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """每日重点：返回各 active 规划当前应聚焦的里程碑（最多 3 条）。"""
    return get_daily_focus(db, user.id)


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


@router.post(
    "/{plan_id}/milestones/{idx}/logs",
    response_model=MilestoneLogResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_log(
    plan_id: UUID,
    idx: int,
    body: MilestoneLogCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """为指定里程碑添加执行日志。"""
    log = add_milestone_log(db, user.id, plan_id, idx, body.content)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="规划或里程碑不存在"
        )
    return log


@router.get(
    "/{plan_id}/milestones/{idx}/logs",
    response_model=list[MilestoneLogResponse],
)
def list_logs(
    plan_id: UUID,
    idx: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出指定里程碑的执行日志。"""
    return list_milestone_logs(db, user.id, plan_id, idx)


@router.delete("/{plan_id}/logs/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_log(
    plan_id: UUID,
    log_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除一条执行日志。"""
    deleted = delete_milestone_log(db, user.id, str(log_id))
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="日志不存在"
        )
    return None
