from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.retrospective import PeriodType


class RetroCreate(BaseModel):
    period_type: PeriodType
    period_start: date
    period_end: date
    title: str = Field(min_length=1, max_length=255)
    achievements: list[str] = Field(default_factory=list)
    challenges: str | None = None
    lessons_learned: str | None = None
    next_steps: list[str] = Field(default_factory=list)
    satisfaction: int = Field(ge=1, le=5)


class RetroUpdate(BaseModel):
    period_type: PeriodType | None = None
    period_start: date | None = None
    period_end: date | None = None
    title: str | None = None
    achievements: list[str] | None = None
    challenges: str | None = None
    lessons_learned: str | None = None
    next_steps: list[str] | None = None
    satisfaction: int | None = Field(default=None, ge=1, le=5)


class RetroResponse(BaseModel):
    id: UUID
    user_id: UUID
    period_type: PeriodType
    period_start: date
    period_end: date
    title: str
    achievements: list[str]
    challenges: str | None
    lessons_learned: str | None
    next_steps: list[str]
    satisfaction: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventSummary(BaseModel):
    id: UUID
    event_date: date
    event_type: str
    title: str


class RetroDraft(BaseModel):
    period_start: date
    period_end: date
    event_summaries: list[EventSummary]
    suggested_achievements: list[str]


# ======================================================================
# AI 复盘草稿
# ======================================================================

class AIRetroDraftRequest(BaseModel):
    """AI 复盘草稿请求体。"""

    period_start: date = Field(..., description="复盘时段开始日期")
    period_end: date = Field(..., description="复盘时段结束日期")

    @model_validator(mode="after")
    def _check_period_order(self):
        """period_end 不得早于 period_start。"""
        if self.period_end < self.period_start:
            raise ValueError("period_end 不能早于 period_start")
        return self


class AIRetroDraftResponse(BaseModel):
    """AI 复盘草稿响应体（对应 LLM 输出的 JSON 结构）。"""

    achievements: list[str]
    challenges: str
    lessons_learned: str
    next_steps: list[str]
    suggested_satisfaction: int
    summary: str
