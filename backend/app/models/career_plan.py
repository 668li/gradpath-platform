# backend/app/models/career_plan.py
"""职业规划模型 — Phase 11 AI 职业管家的规划产物。

由 CareerPlanningSkill 解析 LLM 输出生成，记录目标、当前状态、目标状态、
能力差距、里程碑与时间线，供用户跟踪执行进度。
"""
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class CareerPlan(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "career_plans"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id"), nullable=True
    )
    goal_text: Mapped[str] = mapped_column(Text, nullable=False)
    current_state: Mapped[dict] = mapped_column(JSONB, default=dict)  # {skills, education, experience}
    target_state: Mapped[dict] = mapped_column(JSONB, default=dict)  # {position, company, requirements}
    gaps: Mapped[list] = mapped_column(JSONB, default=list)  # [{skill, current_level, target_level, gap}]
    milestones: Mapped[list] = mapped_column(JSONB, default=list)  # [{title, description, deadline, skills[], status}]
    timeline_months: Mapped[int] = mapped_column(Integer, default=6)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft/active/completed
