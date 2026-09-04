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
        description="审计聚焦领域",
    )


# ======================================================================
# 人生设计蓝图（认识自己 V1：访谈 ⟨DONE⟩ 轮产出）
# ======================================================================

class BlueprintTranscriptItem(BaseModel):
    """访谈问答记录条目。"""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=100000)
    stage: str | None = Field(default=None, max_length=10)


class BlueprintCreate(BaseModel):
    """保存人生设计蓝图。"""

    content: str = Field(..., min_length=50, max_length=100000)
    title: str | None = Field(default=None, max_length=200)
    conversation_id: UUID | None = None
    transcript: list[BlueprintTranscriptItem] = Field(default_factory=list)
    status: str = Field(default="completed", pattern="^(draft|completed)$")


class BlueprintResponse(BaseModel):
    id: UUID
    title: str
    content: str
    status: str
    version: int
    conversation_id: UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BlueprintSummary(BaseModel):
    """列表项：不含全文，避免一次拉多份 8000+ 字。"""

    id: UUID
    title: str
    status: str
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}
