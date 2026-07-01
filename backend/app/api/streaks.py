"""连续打卡 API — 损失厌恶驱动的留存机制。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.streak import StreakResponse
from app.services import streak_service

router = APIRouter(prefix="/api/streaks", tags=["连续打卡"])


@router.get("/stats", response_model=StreakResponse)
def get_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前连续打卡统计。"""
    return streak_service.get_streak_stats(db, user.id)
