"""学习资源模型"""
from sqlalchemy import String, Integer, Boolean, Date, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin, GUID, JSONB
from uuid import UUID
from typing import Optional


class LearningResource(UUIDMixin, TimestampMixin, Base):
    """学习资源"""
    __tablename__ = "learning_resources"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # video/book/course/article
    subject: Mapped[str] = mapped_column(String(100), nullable=False)  # 数学/英语/408/政治
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)  # beginner/intermediate/advanced
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1-5
    is_free: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
