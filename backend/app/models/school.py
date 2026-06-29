# backend/app/models/school.py
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class School(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(10))
    report_index_url: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(String(20))
    level: Mapped[str | None] = mapped_column(String(20))  # 985/211/双一流/普通

    reports: Mapped[list["ReportRecord"]] = relationship(back_populates="school")
