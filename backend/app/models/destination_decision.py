import enum
from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class DestinationType(str, enum.Enum):
    employment = "employment"
    postgrad = "postgrad"
    civil_service = "civil_service"
    abroad = "abroad"
    phd = "phd"
    startup = "startup"
    gap_year = "gap_year"


class DecisionStatus(str, enum.Enum):
    planned = "planned"
    confirmed = "confirmed"
    executed = "executed"
    changed = "changed"


class DestinationDecision(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "destination_decisions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    decision_date: Mapped[date] = mapped_column(Date, nullable=False)
    destination_type: Mapped[DestinationType] = mapped_column(Enum(DestinationType), nullable=False)
    status: Mapped[DecisionStatus] = mapped_column(Enum(DecisionStatus), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_snapshot_id: Mapped[UUID | None] = mapped_column(nullable=True)
    # 决策日志字段 — 护城河功能：决策回溯与结果追踪
    prediction: Mapped[str | None] = mapped_column(Text, nullable=True)
    assumptions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
