# backend/app/models/growth_insight.py
"""成长洞察模型 — 缓存 LLM 生成的成长分析结果，按 event_count 判断是否需要重新生成。"""
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class GrowthInsight(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "growth_insights"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    insight_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )
