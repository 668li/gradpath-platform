"""学习计划模型"""
from sqlalchemy import String, Integer, Boolean, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin, GUID, JSONB
from uuid import UUID
from typing import Optional


class StudyPlan(UUIDMixin, TimestampMixin, Base):
    """学习计划"""
    __tablename__ = "study_plans"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    end_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    subjects: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 0-100
