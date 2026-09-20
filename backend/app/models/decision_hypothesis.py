"""决策假设模型。

Decision OS 的最小一等公民：把 DestinationDecision 里的 assumptions
从不可计算的字符串升级为可验证、可被证据支持/反驳的结构化对象。
"""

from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class DecisionHypothesis(UUIDMixin, TimestampMixin, Base):
    """一条需要被证据验证的决策假设。"""

    __tablename__ = "decision_hypotheses"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("destination_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    # 1=低重要性，5=决定性假设；用于后续优先验证排序。
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # 当前主观置信度 0~1，不代表客观概率。
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.5)
    # open / validated / invalidated / superseded
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    # 验证这个假设时，系统希望用户回答的具体问题。
    verification_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 最小验证行动，例如“分析 20 个目标岗位学历要求”。
    validation_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 后续规则/AI 可扩展字段，不把推理结果硬塞进文本。
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
