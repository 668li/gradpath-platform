# backend/app/api/career_profile.py
"""用户职业画像 API 路由。

- GET /api/career-profile — 获取当前用户的画像（不存在则返回 null）
- POST /api/career-profile — 创建画像（已存在则 400）
- PUT /api/career-profile — 更新画像（不存在则 404）
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.career_profile import CareerProfile
from app.models.user import User
from app.schemas.career_profile import (
    CareerProfileCreate,
    CareerProfileResponse,
    CareerProfileUpdate,
)

router = APIRouter(prefix="/api/career-profile", tags=["职业画像"])


@router.get("", response_model=CareerProfileResponse | None)
def get_profile(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取当前用户的职业画像，不存在则返回 null。"""
    return (
        db.query(CareerProfile)
        .filter(CareerProfile.user_id == user.id)
        .first()
    )


@router.post(
    "",
    response_model=CareerProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_profile(
    body: CareerProfileCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建职业画像。已存在则返回 400。"""
    existing = (
        db.query(CareerProfile)
        .filter(CareerProfile.user_id == user.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="职业画像已存在"
        )
    profile = CareerProfile(user_id=user.id, **body.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.put("", response_model=CareerProfileResponse)
def update_profile(
    body: CareerProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新职业画像。不存在则返回 404。"""
    profile = (
        db.query(CareerProfile)
        .filter(CareerProfile.user_id == user.id)
        .first()
    )
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="职业画像不存在"
        )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
