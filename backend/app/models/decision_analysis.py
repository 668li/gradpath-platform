"""决策分析模型 — 预验尸(Pre-mortem) + 决策矩阵 + 红队质疑。

在决策前就预想失败，用加权矩阵量化选项，用红队问题检验假设。
真正提升决策质量，而非事后归因。
"""
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class DecisionAnalysis(UUIDMixin, TimestampMixin, Base):
    """决策深度分析 — 预验尸 + 矩阵 + 红队。"""
    __tablename__ = "decision_analyses"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 关联的决策 ID（可选，也可以是独立分析）
    decision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("destination_decisions.id", ondelete="SET NULL"), nullable=True
    )
    # 分析标题
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 被分析的选项列表
    options: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # === 预验尸分析 ===
    # "假设6个月后这个决策结果很糟，列出10-15个原因"
    premortem_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 聚类后的风险类别
    premortem_categories: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 针对每个类别的保障措施
    safeguards: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # === 决策矩阵 ===
    # 评估标准 [{criterion, weight}] 权重总和 100
    criteria: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 评分矩阵 [{option, scores: {criterion: score}}] 1-10 分
    matrix_scores: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 加权总分 [{option, total_score}]
    weighted_results: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 矩阵赢家
    winner: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # === 红队质疑 ===
    red_team_questions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    red_team_answers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # === AI 综合分析 ===
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 最终建议
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
