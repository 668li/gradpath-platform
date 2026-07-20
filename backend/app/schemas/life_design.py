"""人生设计引擎 Schemas。"""
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AuditQuestion(BaseModel):
    question: str
    answer: str = ""


class SprintGoal(BaseModel):
    title: str
    measurable_result: str
    deadline: date | None = None


class SprintCreate(BaseModel):
    name: str = Field(..., max_length=200)
    primary_domain: str
    maintenance_domains: list[str] = Field(default_factory=list)
    start_date: date
    end_date: date
    goals: list[SprintGoal] = Field(default_factory=list)
    vision_statement: str | None = None
    audit_summary: str | None = None
    audit_qa: list[AuditQuestion] = Field(default_factory=list)


class SprintResponse(BaseModel):
    id: UUID
    name: str
    primary_domain: str
    maintenance_domains: list
    start_date: date
    end_date: date
    status: str
    goals: list
    vision_statement: str | None
    audit_summary: str | None
    audit_qa: list
    review_notes: str | None
    ai_review: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WeeklyReviewCreate(BaseModel):
    sprint_id: UUID | None = None
    week_start: date
    week_end: date
    planned_actions: str | None = None
    actual_actions: str | None = None
    what_worked: str | None = None
    what_didnt_work: str | None = None
    next_week_plan: str | None = None
    energy_level: int | None = Field(default=None, ge=1, le=5)


class WeeklyReviewResponse(BaseModel):
    id: UUID
    sprint_id: UUID | None
    week_start: date
    week_end: date
    planned_actions: str | None
    actual_actions: str | None
    what_worked: str | None
    what_didnt_work: str | None
    next_week_plan: str | None
    energy_level: int | None
    ai_analysis: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditGenerateRequest(BaseModel):
    """请求 AI 生成个性化的人生审计问题。"""
    focus_areas: list[str] = Field(
        default_factory=lambda: ["career", "finance", "health", "relationships", "growth"],
        description="审计聚焦领域"
    )
