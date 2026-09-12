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


class ActionHook(BaseModel):
    """回答尾部行动钩子（speckit 003）：服务端模板+真实库判定，非 LLM 文本。

    语义约束见 specs/003-ai-chat-stickiness/contracts/chat-api.md：
    每轮 ≤2 个；"已做过"不重复推销；服务异常时整段为 None（降级负例）。
    """

    type: str  # subscribe_timeline / feedback_node / micro_checkin / explore
    text: str
    link: str | None = None


class SendMessageResponse(BaseModel):
    content: str
    skill_used: str
    career_plan: str | None = None  # 保存的 CareerPlan ID
    micro_action_plan: str | None = None  # 学习计划师落库的 7 天微行动计划 ID
    # 站内数据搜索层带回的真实数据来源（前端气泡「参考来源」标签+置信度条）
    agent_sources: list[dict] | None = None
    agent_confidence: float | None = None
    # 行动钩子（speckit 003 FR2/FR7）：可执行动作入口；None=无钩子/降级
    action_hooks: list[ActionHook] | None = None


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
    # 修复: FASTAPI-VALID-001 — 里程碑日志 content 加 max_length
    content: str = Field(..., min_length=1, max_length=5000)


class MilestoneLogResponse(BaseModel):
    id: UUID
    plan_id: UUID
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
