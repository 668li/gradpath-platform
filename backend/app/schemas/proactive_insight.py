from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProactiveInsightResponse(BaseModel):
    id: UUID
    insight_type: str
    title: str
    content: str
    action_suggestion: str | None
    priority: int
    related_data: dict
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ProactiveInsightSummary(BaseModel):
    unread_count: int
    total_count: int
    latest_insights: list[ProactiveInsightResponse]
