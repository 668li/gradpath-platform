"""成长快照模型 — 让成长模式分析可持久化、可跨期对比（护城河补充）。"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class GrowthSnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "growth_snapshots"

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 分析周期标签，如 2026-07（按月）
    period: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    growth_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pattern_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 完整分析结果（JSON 字符串），便于历史回看
    snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
