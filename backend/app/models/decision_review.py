"""决策回顾任务队列 — 决策飞轮护城河。

用户每次创建决策时，自动入队一条回顾任务（scheduled_at = decision.review_date）。
到期后系统推送通知，用户完成回顾后 AI 对比 prediction vs actual_outcome，
累积决策准确率模型，反哺用户画像。
"""
import enum
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class ReviewStatus(str, enum.Enum):
    """回顾任务状态 — 决策飞轮生命周期的状态机。"""
    pending = "pending"        # 待回顾（未到 scheduled_at 或已到未完成）
    notified = "notified"      # 已推送通知（用户未操作）
    completed = "completed"    # 已完成回顾（AI 已生成分析）
    skipped = "skipped"        # 用户主动跳过
    cancelled = "cancelled"    # 决策变更，回顾取消


class DecisionReviewQueue(UUIDMixin, TimestampMixin, Base):
    """决策回顾任务 — 与 DestinationDecision 一对一关联。

    设计：
    - scheduled_at 由决策的 review_date 决定
    - status 流转：pending → notified → completed/skipped/cancelled
    - ai_review_result 存储 AI 对比分析结果（结构化 JSONB）
    - 完成后 completed_at 记录时间，用于准确率统计
    """
    __tablename__ = "decision_review_queue"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("destination_decisions.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # === 调度信息 ===
    scheduled_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus), nullable=False, default=ReviewStatus.pending, index=True
    )

    # === 用户回顾输入 ===
    # actual_outcome: 用户回顾时填写的实际结果
    actual_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    # review_notes: 用户的反思笔记
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # satisfaction: 1-5 分，对决策结果的主观满意度
    satisfaction: Mapped[int | None] = mapped_column(nullable=True)

    # === AI 分析结果 ===
    # ai_review_result: 结构化 JSON，含 prediction_match / accuracy_score / insights / lessons
    ai_review_result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
