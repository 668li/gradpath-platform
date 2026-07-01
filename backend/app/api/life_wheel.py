"""人生平衡轮 API — 8 维度生活满意度评估。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.life_wheel import LifeWheelAnalyzeRequest, LifeWheelResponse, LifeWheelSubmit
from app.services import life_wheel_service

router = APIRouter(prefix="/api/life-wheel", tags=["人生平衡轮"])


@router.post("/submit", response_model=LifeWheelResponse, status_code=status.HTTP_201_CREATED)
def submit(
    body: LifeWheelSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交一次人生平衡轮评估。"""
    snapshot = life_wheel_service.submit_scores(db, user.id, body.scores, body.notes)
    return LifeWheelResponse.model_validate(snapshot)


@router.get("/latest", response_model=LifeWheelResponse | None)
def get_latest(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取最近一次评估。"""
    snapshot = life_wheel_service.get_latest(db, user.id)
    return LifeWheelResponse.model_validate(snapshot) if snapshot else None


@router.get("/history", response_model=list[LifeWheelResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取历史评估记录。"""
    snapshots = life_wheel_service.get_history(db, user.id)
    return [LifeWheelResponse.model_validate(s) for s in snapshots]


@router.get("/dimensions")
def get_dimensions():
    """获取 8 个维度定义（无需认证）。"""
    return life_wheel_service.LIFE_DIMENSIONS


@router.post("/analyze", response_model=dict)
def analyze(
    body: LifeWheelAnalyzeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """为指定快照生成 AI 分析建议。"""
    analysis = life_wheel_service.generate_ai_analysis(db, body.snapshot_id)
    return {"ai_analysis": analysis}
