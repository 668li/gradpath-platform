# backend/app/schemas/career_profile.py
"""用户职业画像 Schema 定义。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CareerProfileBase(BaseModel):
    education_level: str | None = None
    major: str | None = None
    school_name: str | None = None
    school_tier: str | None = None
    graduation_year: int | None = None
    target_direction: str | None = None
    target_industry: str | None = None
    technical_skill: int = Field(default=3, ge=1, le=5)
    communication_skill: int = Field(default=3, ge=1, le=5)
    leadership_skill: int = Field(default=3, ge=1, le=5)
    creativity_skill: int = Field(default=3, ge=1, le=5)
    self_introduction: str | None = None


class CareerProfileCreate(CareerProfileBase):
    pass


class CareerProfileUpdate(CareerProfileBase):
    pass


class CareerProfileResponse(CareerProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
