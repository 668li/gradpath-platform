from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.career_event import EventType


class EventCreate(BaseModel):
    event_date: date
    event_type: EventType
    title: str = Field(min_length=1, max_length=255)
    # 修复: FASTAPI-VALID-001 — STAR 各字段加 max_length 防止超大文本
    description: str | None = Field(None, max_length=5000)
    situation: str | None = Field(None, max_length=5000)
    task: str | None = Field(None, max_length=5000)
    action: str | None = Field(None, max_length=10000)
    result: str | None = Field(None, max_length=5000)
    reflection: str | None = Field(None, max_length=5000)
    skills_gained: list[str] = Field(default_factory=list)
    impact_metrics: dict | None = None
    mood: int | None = Field(default=None, ge=1, le=5)


class EventUpdate(BaseModel):
    event_date: date | None = None
    event_type: EventType | None = None
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=5000)
    situation: str | None = Field(None, max_length=5000)
    task: str | None = Field(None, max_length=5000)
    action: str | None = Field(None, max_length=10000)
    result: str | None = Field(None, max_length=5000)
    reflection: str | None = Field(None, max_length=5000)
    skills_gained: list[str] | None = None
    impact_metrics: dict | None = None
    mood: int | None = Field(default=None, ge=1, le=5)


class EventResponse(BaseModel):
    id: UUID
    user_id: UUID
    event_date: date
    event_type: EventType
    title: str
    description: str | None
    situation: str | None
    task: str | None
    action: str | None
    result: str | None
    reflection: str | None
    skills_gained: list[str]
    impact_metrics: dict | None
    mood: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
