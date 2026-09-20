"""Structured outcome and reflection for Decision OS."""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class DecisionOutcome(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "decision_outcomes"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    outcome_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # direct / partial / unobservable / counterfactual_unknown
    observed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)


class DecisionReflection(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "decision_reflections"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    outcome_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("decision_outcomes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    prediction_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    wrong_assumption: Mapped[str | None] = mapped_column(Text, nullable=True)
    omitted_factor: Mapped[str | None] = mapped_column(Text, nullable=True)
    lesson: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
