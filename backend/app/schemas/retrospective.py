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


# ======================================================================
# 复盘深化（2026-09-25）：原则库 / Try 行动卡 / 引导反思
# ======================================================================


class PrincipleCreate(BaseModel):
    """创建原则（默认 draft 态）。"""

    trigger_scene: str = Field(min_length=6, max_length=200)
    action: str = Field(min_length=6, max_length=400)
    rationale: str | None = Field(default=None, max_length=500)
    scene_tags: list[str] = Field(default_factory=list, max_length=5)
    source_retro_id: UUID | None = None


class PrincipleUpdate(BaseModel):
    trigger_scene: str | None = Field(default=None, min_length=6, max_length=200)
    action: str | None = Field(default=None, min_length=6, max_length=400)
    rationale: str | None = Field(default=None, max_length=500)
    scene_tags: list[str] | None = Field(default=None, max_length=5)


class PrincipleVerifyRequest(BaseModel):
    """原则复审裁决：again（再次有效）/ ineffective（失效）/ pending（还没遇到）。"""

    verdict: str = Field(pattern="^(again|ineffective|pending)$")
    note: str | None = Field(default=None, max_length=500)


class ActionCreateItem(BaseModel):
    content: str = Field(min_length=1, max_length=400)
    trigger_scene: str = Field(min_length=4, max_length=200)
    review_due_at: date | None = None


class ActionsCreateRequest(BaseModel):
    """为某次复盘创建 Try 行动卡（≤3 条，KPT 铁律）。"""

    retro_id: UUID
    items: list[ActionCreateItem] = Field(min_length=1, max_length=3)


class ActionReviewRequest(BaseModel):
    """行动卡复审裁决：effective / ineffective / not_met。"""

    verdict: str = Field(pattern="^(effective|ineffective|not_met)$")
    note: str | None = Field(default=None, max_length=500)


class ReflectRequest(BaseModel):
    """AI 教练引导反思：前端持有对话历史，每轮取下一问。"""

    messages: list[dict] = Field(min_length=1, max_length=40)
    period_start: date | None = None
    period_end: date | None = None

    @model_validator(mode="after")
    def _check_messages(self):
        for m in self.messages:
            if not isinstance(m, dict) or m.get("role") not in {"user", "coach"}:
                raise ValueError("messages 须为 [{role: user|coach, content: str}]")
            m["content"] = str(m.get("content", ""))[:2000]
        return self


class PrincipleDraftRequest(BaseModel):
    """从复盘内容提炼原则草稿。"""

    retro_content: str = Field(min_length=20, max_length=4000)
    source_retro_id: UUID | None = None
    period_start: date | None = None
    period_end: date | None = None
