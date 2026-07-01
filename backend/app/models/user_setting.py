# backend/app/models/user_setting.py
"""用户设置模型 — 技能分享开关与分享令牌。"""
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class UserSetting(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_settings"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    share_skills_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True, index=True)
