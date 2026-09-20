"""Structured prediction for Decision OS.

Prediction is a falsifiable claim, not free-form confidence text.
"""

from datetime import date
from uuid import UUID

from sqlalchemy import Date, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class DecisionPrediction(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "decision_predictions"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    decision_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("destination_decisions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(200), nullable=False)
    target: Mapped[str] = mapped_column(Text, nullable=False)
    probability: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0~1
    horizon: Mapped[date | None] = mapped_column(Date, nullable=True)
    success_condition: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
