import enum
from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class PeriodType(str, enum.Enum):
    annual = "annual"
    quarterly = "quarterly"
    project = "project"
    custom = "custom"


class Retrospective(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "retrospectives"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    period_type: Mapped[PeriodType] = mapped_column(Enum(PeriodType), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    achievements: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    challenges: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    satisfaction: Mapped[int] = mapped_column(Integer, nullable=False)
