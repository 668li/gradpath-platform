from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class TimelineItem(BaseModel):
    id: UUID
    date: date
    type: str  # "decision" 或 "event"
    title: str
    subtitle: str | None = None


class DashboardOverview(BaseModel):
    decisions_count: int
    events_count: int
    skills_count: int
    retrospectives_count: int
    latest_decision: dict | None = None
    recent_events: list[dict] = []
    skill_categories: dict[str, int] = {}
    latest_retrospective: dict | None = None
    timeline: list[TimelineItem] = []
