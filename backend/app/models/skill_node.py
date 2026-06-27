from datetime import date
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class SkillNode(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "skill_nodes"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("skill_nodes.id"), nullable=True)
    acquired_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    children: Mapped[list["SkillNode"]] = relationship(
        "SkillNode",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    parent: Mapped["SkillNode | None"] = relationship(
        "SkillNode",
        back_populates="children",
        remote_side="SkillNode.id",
    )
