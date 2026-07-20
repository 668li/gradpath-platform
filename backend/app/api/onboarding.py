"""Onboarding API — 首次诊断接口。

GET /api/onboarding: 查询用户 onboarding 状态
POST /api/onboarding: 保存诊断答案（不生成 AI 诊断）
POST /api/onboarding/generate: 生成 AI 诊断
POST /api/onboarding/skip: 跳过 onboarding
GET /api/onboarding/status: 检查是否已完成
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.onboarding_service import (
    create_onboarding,
    generate_diagnosis,
    get_onboarding,
    is_onboarding_completed,
    skip_onboarding,
)

router = APIRouter(prefix="/api/onboarding", tags=["首次诊断"])


class OnboardingRequest(BaseModel):
    current_stage: str = Field(..., max_length=50, description="当前阶段")
    target_direction: str = Field(..., max_length=50, description="目标方向")
    target_industry: str | None = Field(None, max_length=100, description="目标行业")
    self_assessment: dict = Field(default_factory=dict, description="自我评估答案")


def _serialize(ob):
    return {
        "id": str(ob.id),
        "current_stage": ob.current_stage,
        "target_direction": ob.target_direction,
        "target_industry": ob.target_industry,
        "self_assessment": ob.self_assessment,
        "status": ob.status.value if hasattr(ob.status, "value") else str(ob.status),
        "ai_diagnosis": ob.ai_diagnosis,
        "recommended_path": ob.recommended_path,
        "key_insights": ob.key_insights,
        "completed_at": ob.completed_at.isoformat() if ob.completed_at else None,
        "created_at": ob.created_at.isoformat() if ob.created_at else None,
    }


@router.get("")
def get(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询用户最新的 onboarding 记录。"""
    ob = get_onboarding(db, user.id)
    if not ob:
        return {"onboarding": None, "completed": False}
    return {"onboarding": _serialize(ob), "completed": ob.status.value == "completed"}


@router.get("/status")
def get_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """检查是否已完成 onboarding。"""
    return {"completed": is_onboarding_completed(db, user.id)}


@router.post("", status_code=status.HTTP_201_CREATED)
def save(
    req: OnboardingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存诊断答案（状态为 in_progress，不生成 AI 诊断）。"""
    ob = create_onboarding(
        db=db,
        user_id=user.id,
        current_stage=req.current_stage,
        target_direction=req.target_direction,
        target_industry=req.target_industry,
        self_assessment=req.self_assessment,
    )
    return _serialize(ob)


@router.post("/generate")
async def generate(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """生成 AI 诊断 + 推荐路径。"""
    ob = get_onboarding(db, user.id)
    if not ob:
        raise HTTPException(status_code=404, detail="请先保存诊断答案")
    try:
        ob = await generate_diagnosis(db, ob.id)
    except Exception:
        raise HTTPException(status_code=503, detail="AI 服务暂不可用，请稍后重试")
    return _serialize(ob)


@router.post("/skip")
def skip(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """跳过 onboarding。"""
    ob = skip_onboarding(db, user.id)
    return _serialize(ob)
