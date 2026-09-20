"""决策证据模型。

Evidence 不等于“引用一段内容”。它描述一条针对决策/假设的可追溯事实，
并明确来源、立场和可靠性，供后续 Evidence Provider 与决策引擎消费。
"""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class DecisionEvidence(UUIDMixin, TimestampMixin, Base):
    """与决策或某条假设关联的一条证据。"""

    __tablename__ = "decision_evidence"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        GUID(),
        ForeignKey("destination_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hypothesis_id: Mapped[UUID | None] = mapped_column(
        GUID(),
        ForeignKey("decision_hypotheses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 证据支持的具体事实/结论，而不是泛泛“有研究表明”。
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    # official / dataset / peer / user / research / other
    source_type: Mapped[str] = mapped_column(String(30), nullable=False, default="other")
    # 1~5，5 为用户/系统确认的高可信来源。
    reliability: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # supports / refutes / neutral
    stance: Mapped[str] = mapped_column(String(20), nullable=False, default="neutral")
    observed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 原文短摘录，保留审计线索；不要保存整篇外部内容。
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Evidence Provider 与验证链：内部数据默认不等于已核实事实。
    provider_name: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="internal_unverified", index=True
    )
    verification_source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True
    )
    verified_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
