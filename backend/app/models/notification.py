"""通知模型 — 系统通知、活动提醒、评论回复等。"""
import enum
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class NotificationType(str, enum.Enum):
    system = "system"
    comment = "comment"
    reply = "reply"
    achievement = "achievement"
    reminder = "reminder"
    new_post = "new_post"
    new_follower = "new_follower"


class Notification(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType), nullable=False, default=NotificationType.system
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="点击通知后跳转的链接")
    read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
