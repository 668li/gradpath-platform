"""讨论帖模型 — 用户围绕"学校专业去向"或"公司岗位面试"主题发帖讨论。"""
import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class PostTopicType(str, enum.Enum):
    school_major = "school_major"
    company_position = "company_position"


class Post(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "posts"
    # 复合索引：按主题类型+主题键查询帖子是最高频操作（社区讨论区入口）
    # 单列索引：user_id（用户发帖历史）、parent_id（查询回复列表）
    __table_args__ = (
        Index("ix_posts_topic_type_key", "topic_type", "topic_key"),
    )

    topic_type: Mapped[PostTopicType] = mapped_column(
        Enum(PostTopicType), nullable=False
    )
    topic_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=True, index=True
    )

    # 自引用关系：顶层帖的 replies 列表
    replies: Mapped[list["Post"]] = relationship(
        "Post",
        back_populates="parent",
        cascade="all, delete-orphan",
        foreign_keys=[parent_id],
    )
    parent: Mapped["Post | None"] = relationship(
        "Post",
        back_populates="replies",
        remote_side="Post.id",
        foreign_keys=[parent_id],
    )
