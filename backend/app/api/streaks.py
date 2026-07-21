"""连续打卡 API — 损失厌恶驱动的留存机制。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.streak import (
    StreakCheckInRequest,
    StreakCheckInResponse,
    StreakRedeemResponse,
    StreakResponse,
    StreakRestDayResponse,
)
from app.services import streak_service

router = APIRouter(prefix="/api/streaks", tags=["连续打卡"])


@router.get("/stats", response_model=StreakResponse)
def get_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前连续打卡统计（含里程碑、休息日、回赎状态）。"""
    return streak_service.get_streak_stats(db, user.id)


@router.post("/checkin", response_model=StreakCheckInResponse)
def checkin(
    body: StreakCheckInRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动打卡：完成今日行动后调用。

    action_type: "main"（主行动）或 "micro"（微行动）。
    完成主行动得10XP，微行动得3XP。
    """
    return streak_service.checkin(db, user.id, body.action_type, body.action_detail)


@router.post("/rest-day", response_model=StreakRestDayResponse)
def rest_day(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记今天为休息日（每周1次），不扣streak。"""
    return streak_service.rest_day(db, user.id)


@router.post("/redeem", response_model=StreakRedeemResponse)
def redeem(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """断签回赎：完成双倍行动日（主+微都完成）后可赎回1次断签。"""
    return streak_service.redeem_streak(db, user.id)
