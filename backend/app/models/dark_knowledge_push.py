"""暗知识主动推送日志 — 暗知识护城河。

将 1020 条暗知识从"被动检索"改为"主动推送"：
根据用户当前阶段 + 行为画像，主动推送最相关的暗知识，
并跟踪阅读 + 反馈，形成"推送→阅读→反馈→优化"闭环。
"""
import enum
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class PushFeedback(str, enum.Enum):
    """推送反馈 — 用于优化推送策略。"""
    none = "none"             # 未反馈
    positive = "positive"     # 有用
    negative = "negative"     # 无用/不相关
    later = "later"           # 稍后看


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DarkKnowledgePushLog(UUIDMixin, TimestampMixin, Base):
    """暗知识推送日志 — 记录每次推送 + 用户反馈。

    设计：
    - 一条暗知识对同一用户最多推送一次（user_id + dark_knowledge_id 唯一约束）
    - pushed_at 记录推送时间，read_at 记录阅读时间
    - feedback + feedback_notes 记录用户反馈
    - 推送策略基于：用户阶段 / 当前决策 / 历史阅读
    """
    __tablename__ = "dark_knowledge_push_log"
    __table_args__ = (
        # 索引：按用户+推送时间排序，便于查询用户的推送流
        # 唯一性约束（user_id + dark_knowledge_id）由应用层保证，
        # 避免 SQLite 不支持部分唯一索引的兼容性问题
    )

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dark_knowledge_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("dark_knowledge.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # === 推送上下文 ===
    # 推送时的用户阶段快照（用于后续分析推送效果）
    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # 推送原因（结构化 JSON，如 {"trigger": "decision_created", "decision_id": "..."}）
    push_reason: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    pushed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # === 用户反馈 ===
    feedback: Mapped[PushFeedback] = mapped_column(
        Enum(PushFeedback), nullable=False, default=PushFeedback.none
    )
    feedback_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 用户评分 1-5（可选）
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
