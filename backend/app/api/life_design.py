"""人生设计引擎 API — AI Life Design 七步法。"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.life_design import (
    AuditGenerateRequest,
    SprintCreate,
    SprintResponse,
    WeeklyReviewCreate,
    WeeklyReviewResponse,
)
from app.services import life_design_service

router = APIRouter(prefix="/api/life-design", tags=["人生设计引擎"])


@router.post("/audit/questions")
def generate_audit_questions(body: AuditGenerateRequest):
    """生成人生审计问题（基于问题库，无需 LLM）。"""
    return life_design_service.generate_audit_questions(body.focus_areas)


@router.post("/audit/generate-vision")
async def generate_vision(
    body: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """基于审计问答，AI 生成愿景声明。"""
    vision = await life_design_service.generate_vision_from_audit(db, user.id, body.get("audit_qa", []))
    return {"vision_statement": vision}


@router.post("/sprints", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
def create_sprint(
    body: SprintCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建一个 90 天冲刺。"""
    sprint = life_design_service.create_sprint(db, user.id, body.model_dump())
    return SprintResponse.model_validate(sprint)


@router.get("/sprints", response_model=list[SprintResponse])
def list_sprints(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取所有冲刺。"""
    sprints = life_design_service.get_sprints(db, user.id)
    return [SprintResponse.model_validate(s) for s in sprints]


@router.get("/sprints/active", response_model=SprintResponse | None)
def get_active_sprint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前活跃冲刺。"""
    sprint = life_design_service.get_active_sprint(db, user.id)
    return SprintResponse.model_validate(sprint) if sprint else None


@router.post("/sprints/{sprint_id}/activate", response_model=SprintResponse)
def activate_sprint(
    sprint_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """激活一个冲刺。"""
    # 修复 bug: service 层 raise ValueError("冲刺不存在") -> 500，应转 404
    try:
        sprint = life_design_service.activate_sprint(db, user.id, sprint_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return SprintResponse.model_validate(sprint)


@router.post("/sprints/{sprint_id}/review", response_model=dict)
async def generate_sprint_review(
    sprint_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """AI 生成季度回顾分析。"""
    # 修复 bug: service 层 raise ValueError("冲刺不存在") -> 500，应转 404
    try:
        review = await life_design_service.generate_sprint_review(db, sprint_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"ai_review": review}


@router.post("/weekly-reviews", response_model=WeeklyReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_weekly_review(
    body: WeeklyReviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建周复盘（自动生成 AI 分析）。"""
    review = await life_design_service.create_weekly_review(db, user.id, body.model_dump())
    return WeeklyReviewResponse.model_validate(review)


@router.get("/weekly-reviews", response_model=list[WeeklyReviewResponse])
def list_weekly_reviews(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取周复盘历史。"""
    reviews = life_design_service.get_weekly_reviews(db, user.id)
    return [WeeklyReviewResponse.model_validate(r) for r in reviews]
