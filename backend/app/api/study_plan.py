"""学习计划 API"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.study_plan import StudyPlan
from app.schemas.study_plan import (
    StudyPlanCreate,
    StudyPlanUpdate,
    StudyPlanResponse,
)

router = APIRouter(prefix="/api/study-plans", tags=["学习计划"])


@router.post("", response_model=StudyPlanResponse, status_code=status.HTTP_201_CREATED)
def create(
    body: StudyPlanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建学习计划"""
    plan = StudyPlan(user_id=user.id, **body.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.get("", response_model=list[StudyPlanResponse])
def list(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取学习计划列表"""
    return db.query(StudyPlan).filter(StudyPlan.user_id == user.id).all()


@router.get("/{plan_id}", response_model=StudyPlanResponse)
def get(
    plan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单个学习计划"""
    plan = db.query(StudyPlan).filter(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == user.id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    return plan


@router.put("/{plan_id}", response_model=StudyPlanResponse)
def update(
    plan_id: UUID,
    body: StudyPlanUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新学习计划"""
    plan = db.query(StudyPlan).filter(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == user.id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    plan_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除学习计划"""
    plan = db.query(StudyPlan).filter(
        StudyPlan.id == plan_id,
        StudyPlan.user_id == user.id
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="学习计划不存在")
    
    db.delete(plan)
    db.commit()
    return None
