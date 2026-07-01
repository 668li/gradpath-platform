# backend/app/models/milestone_log.py
"""里程碑执行日志模型 — Phase 12。

记录用户对某个里程碑的执行日志/笔记，用于跟踪进度与复盘。
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class MilestoneLog(Base):
    __tablename__ = "milestone_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    plan_id = Column(
        String,
        ForeignKey("career_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    milestone_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
