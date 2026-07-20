"""考研问答回答模型 — 社区交流系统。

核心字段：
- 关联问题：qa_id
- 作者信息：user_id
- 回答内容：content
- 互动统计：点赞数
- 最佳回答：is_best
- 审核机制：待审核/已通过/已拒绝
"""
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class QAAnswer(UUIDMixin, TimestampMixin, Base):
    """考研问答回答表 — 存储对问题的回答。"""
    __tablename__ = "qa_answers"

    # === 关联 ===
    qa_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("qas.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # === 内容 ===
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # === 最佳回答 ===
    is_best: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # === 互动统计 ===
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # === 审核机制 ===
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )  # pending/approved/rejected
