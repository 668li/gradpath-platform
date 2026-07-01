# backend/app/models/user_badge.py
"""用户徽章模型 — 记录用户已获得的徽章（徽章定义在代码 BADGE_REGISTRY 中）。"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class UserBadge(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_code", name="uq_user_badge_code"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    badge_code: Mapped[str] = mapped_column(String(50), nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )
