"""评论模型。"""
import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class Comment(UUIDMixin, TimestampMixin, Base):
    """评论 / 回复"""

    __tablename__ = "comments"

    post_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("experience_posts.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("comments.id", ondelete="CASCADE"), nullable=True, index=True
    )
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    # relationships
    author = relationship("User", lazy="joined", foreign_keys=[user_id])
    replies = relationship("Comment", back_populates="parent", lazy="selectin")
    parent = relationship("Comment", remote_side="Comment.id", back_populates="replies")
