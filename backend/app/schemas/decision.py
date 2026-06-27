from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.destination_decision import DecisionStatus, DestinationType


class DecisionCreate(BaseModel):
    decision_date: date
    destination_type: DestinationType
    status: DecisionStatus = DecisionStatus.planned
    details: dict = Field(default_factory=dict)
    reasoning: str | None = None
    confidence: int = Field(ge=1, le=5)


class DecisionUpdate(BaseModel):
    decision_date: date | None = None
    destination_type: DestinationType | None = None
    status: DecisionStatus | None = None
    details: dict | None = None
    reasoning: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)


class DecisionResponse(BaseModel):
    id: UUID
    user_id: UUID
    decision_date: date
    destination_type: DestinationType
    status: DecisionStatus
    details: dict
    reasoning: str | None
    confidence: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
