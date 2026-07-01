# backend/app/schemas/chat.py
"""对话与职业规划的 Pydantic Schema 定义 — Phase 11。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ======================================================================
# 对话与消息
# ======================================================================

class ConversationCreate(BaseModel):
    title: str = Field(default="新对话", max_length=200)


class ConversationUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


class ConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    active_skills: list = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    skill_used: str | None = None
    context_snapshot: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    skill_hint: str | None = Field(None, max_length=50)


class SendMessageResponse(BaseModel):
    content: str
    skill_used: str
    career_plan: str | None = None  # 保存的 CareerPlan ID


class SkillInfo(BaseModel):
    code: str
    name: str
    description: str
    icon: str


# ======================================================================
# 职业规划
# ======================================================================

class CareerPlanResponse(BaseModel):
    id: UUID
    user_id: UUID
    conversation_id: UUID | None = None
    goal_text: str
    current_state: dict = Field(default_factory=dict)
    target_state: dict = Field(default_factory=dict)
    gaps: list = Field(default_factory=list)
    milestones: list = Field(default_factory=list)
    timeline_months: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MilestoneUpdate(BaseModel):
    status: str = Field(..., max_length=20)


# ======================================================================
# 里程碑执行日志与到期提醒 — Phase 12
# ======================================================================

class MilestoneLogCreate(BaseModel):
    content: str


class MilestoneLogResponse(BaseModel):
    id: str
    plan_id: str
    milestone_index: int
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderItem(BaseModel):
    plan_id: str
    plan_goal: str
    milestone_title: str
    milestone_index: int
    target_date: str | None
    days_remaining: int | None
    type: str  # "overdue" | "upcoming"


class DailyFocusItem(BaseModel):
    plan_id: str
    plan_goal: str
    milestone_title: str
    milestone_index: int
    milestone_description: str
    status: str  # "in_progress" | "pending"
    has_logs: bool
