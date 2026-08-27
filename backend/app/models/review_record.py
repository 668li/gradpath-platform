"""复盘中心契约模型（系统设计 §4.2.7）。

MVP 方案 C：契约先行、实现延后 — 仅落库建表，业务逻辑后续实现。
"""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, BigIntPK, ContractAuditMixin


class ReviewRecord(ContractAuditMixin, Base):
    """复盘记录（t_review_record）。

    review_type：daily / weekly / monthly / milestone。
    status 状态机：DRAFT → PENDING → COMPLETED / FAILED。
    mood_score：1~5 分。
    """

    __tablename__ = "t_review_record"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[UUID] = mapped_column(GUID(), nullable=False)
    review_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # daily / weekly / monthly / milestone
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    action_refs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mood_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1~5
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_insights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_suggestions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    uncertainty_score: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT", server_default=text("'DRAFT'")
    )
    # DRAFT / PENDING / COMPLETED / FAILED
    biz_req_no: Mapped[str | None] = mapped_column(String(64), nullable=True)

    __table_args__ = (
        Index("idx_review_record_user_id_period", "user_id", "period_start", "period_end"),
        Index("idx_review_record_user_id_status", "user_id", "status"),
    )
