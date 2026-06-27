import enum
from datetime import date
from uuid import UUID

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class EventType(str, enum.Enum):
    onboard = "onboard"
    leave = "leave"
    promotion = "promotion"
    transfer = "transfer"
    skill_acquired = "skill_acquired"
    project_done = "project_done"
    certification = "certification"
    other = "other"


class CareerEvent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "career_events"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    situation: Mapped[str | None] = mapped_column(Text, nullable=True)
    task: Mapped[str | None] = mapped_column(Text, nullable=True)
    action: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills_gained: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    impact_metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    mood: Mapped[int | None] = mapped_column(Integer, nullable=True)
