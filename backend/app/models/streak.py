"""连续打卡模型 — 损失厌恶驱动的留存机制。

记录用户每日活跃行为，计算连续打卡天数。
借鉴 Duolingo 的 streak 设计：易维护的连胜才会被维护。
"""
from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class StreakRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "streak_records"
    __table_args__ = (
        UniqueConstraint("user_id", "activity_date", name="uq_streak_user_date"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    activity_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 当日活跃行为类型列表: ["decision", "event", "skill", "plan", "chat", ...]
    activity_types: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 截至当日的连续打卡天数
    streak_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # 是否使用了连胜冻结（类似 Duolingo Streak Freeze）
    freeze_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 当日获得的 XP（用于展示）
    xp_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 是否为休息日（主动标记，不扣streak）
    is_rest_day: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 是否为回赎日（完成双倍行动赎回断签）
    is_redeem: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 行动类型: "main" | "micro" | "rest" | "redeem"
    action_type: Mapped[str] = mapped_column(String(20), nullable=True)
    # 行动详情（用户做了什么）
    action_detail: Mapped[str] = mapped_column(Text, nullable=True)
