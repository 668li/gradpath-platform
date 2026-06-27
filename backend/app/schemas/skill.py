from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.skill_node import SkillNode


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=100)
    level: int = Field(ge=1, le=5)
    parent_id: UUID | None = None
    acquired_date: date | None = None
    notes: str | None = None


class SkillUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    level: int | None = Field(default=None, ge=1, le=5)
    parent_id: UUID | None = None
    acquired_date: date | None = None
    notes: str | None = None


class SkillResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    category: str
    level: int
    parent_id: UUID | None
    acquired_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    children: list["SkillResponse"] = []

    model_config = {"from_attributes": True}


SkillResponse.model_rebuild()
