"""考研问答模型 — 社区交流系统。

核心字段：
- 问题信息：标题/正文/标签/状态
- 作者信息：user_id
- 互动统计：浏览数/回答数
- 解决状态：是否已解决/最佳回答 ID
"""
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.qa_answer import QAAnswer


class QA(UUIDMixin, TimestampMixin, Base):
    """考研问答主表 — 存储考研相关问题。"""
    __tablename__ = "qas"
    __table_args__ = (
        # PostgreSQL 下为 JSONB 列创建 GIN 索引，优化 tags 数组查询
        # postgresql_using 参数仅在 PostgreSQL 下生效，SQLite 会忽略
        Index("ix_qa_tags_gin", "tags", postgresql_using="gin"),
        Index("ix_qa_status_created", "status", "created_at"),
    )

    # === 关联 ===
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 修复 bug: service 层调用 selectinload(QA.answers)，但 model 没有定义该关系
    # 导致 "type object 'QA' has no attribute 'answers'" 错误
    answers: Mapped[list["QAAnswer"]] = relationship(
        "QAAnswer",
        backref="question",
        cascade="all, delete-orphan",
        primaryjoin="QA.id == QAAnswer.qa_id",
        foreign_keys="QAAnswer.qa_id",
        lazy="selectin",
    )

    # === 内容 ===
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # === 审核机制 ===
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # pending/approved/rejected

    # === 互动统计 ===
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # === 解决状态 ===
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    best_answer_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("qa_answers.id", ondelete="SET NULL", use_alter=True), nullable=True, index=True
    )
