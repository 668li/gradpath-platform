from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LifeWheelSubmit(BaseModel):
    scores: dict = Field(..., description="8维度评分 {career, finance, health, relationships, growth, fun, environment, spirituality} 1-10")
    notes: str | None = None


class LifeWheelResponse(BaseModel):
    id: UUID
    snapshot_date: date
    scores: dict
    overall_score: int
    ai_analysis: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LifeWheelAnalyzeRequest(BaseModel):
    snapshot_id: UUID
