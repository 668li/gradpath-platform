# backend/app/api/gamification.py
"""游戏化 API 路由 — XP/等级/徽章档案与用户分享设置。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.gamification import (
    GamificationProfileResponse,
    UserSettingResponse,
    UserSettingUpdate,
)
from app.services.gamification_service import get_profile, get_or_create_settings, update_settings

router = APIRouter(tags=["游戏化"])


@router.get("/api/gamification/profile", response_model=GamificationProfileResponse)
def gamification_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取游戏化档案（XP、等级、徽章）。访问时懒颁发新徽章。"""
    return get_profile(db, user.id)


@router.get("/api/gamification/settings", response_model=UserSettingResponse)
def get_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取用户分享设置。"""
    setting = get_or_create_settings(db, user.id)
    return UserSettingResponse(
        share_skills_enabled=setting.share_skills_enabled,
        share_token=setting.share_token,
    )


@router.patch("/api/gamification/settings", response_model=UserSettingResponse)
def patch_settings(
    body: UserSettingUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新用户分享设置。"""
    setting = update_settings(db, user.id, body.share_skills_enabled)
    return UserSettingResponse(
        share_skills_enabled=setting.share_skills_enabled,
        share_token=setting.share_token,
    )
