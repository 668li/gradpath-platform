"""人生平衡轮模型 — 8 维度生活满意度评估。

定期记录用户在 8 个生活维度的自评分数，形成历史演变曲线。
维度：职业、财务、健康、关系、成长、乐趣、环境、灵性。
"""
from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class LifeWheelSnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "life_wheel_snapshots"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    # scores: {"career": 7, "finance": 5, "health": 8, ...} 1-10 分
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # AI 生成的分析建议
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 用户自述笔记
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 总分（8 维度平均）
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
