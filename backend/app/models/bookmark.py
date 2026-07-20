"""收藏模型 — 用户收藏学校、导师、帖子等内容。"""
import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class BookmarkTargetType(str, enum.Enum):
    school = "school"
    mentor = "mentor"
    post = "post"


class Bookmark(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "target_type", "target_id", name="uq_user_target"),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    target_type: Mapped[BookmarkTargetType] = mapped_column(
        Enum(BookmarkTargetType), nullable=False
    )
    target_id: Mapped[str] = mapped_column(String(500), nullable=False)
