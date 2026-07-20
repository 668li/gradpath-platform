# backend/app/models/milestone_log.py
"""里程碑执行日志模型 — Phase 12。

记录用户对某个里程碑的执行日志/笔记，用于跟踪进度与复盘。
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin


class MilestoneLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "milestone_logs"

    plan_id: Mapped[UUID] = mapped_column(
        ForeignKey("career_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    milestone_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
