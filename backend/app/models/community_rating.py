"""社区评分模型 — 经验贴/知识文章的质量信号。"""
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class CommunityRating(UUIDMixin, TimestampMixin, Base):
    """社区评分 — 用户对经验贴或知识文章的 1-5 星评分 + 评论。"""

    __tablename__ = "community_ratings"
    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_rating_range"),
        Index("ix_community_rating_target", "target_type", "target_id"),
        Index("ix_community_rating_user", "user_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # experience_post / knowledge_article
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str | None] = mapped_column(Text, nullable=True)
