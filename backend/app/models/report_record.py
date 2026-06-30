# backend/app/models/report_record.py
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import UUIDMixin, TimestampMixin
from app.models.pipeline_enums import ContentType, SourceType


class ParseStatus(str, enum.Enum):
    pending = "pending"
    parsed = "parsed"
    failed = "failed"
    reviewed = "reviewed"
    published = "published"


class ReportRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "report_records"
    __table_args__ = (
        UniqueConstraint("school_id", "year", name="uq_school_year"),
    )

    school_id: Mapped[UUID] = mapped_column(ForeignKey("schools.id"), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_html: Mapped[str | None] = mapped_column(Text)
    raw_pdf_path: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType), default=SourceType.crawl, nullable=False
    )
    content_type: Mapped[ContentType | None] = mapped_column(Enum(ContentType))
    file_path: Mapped[str | None] = mapped_column(String(500))
    parse_status: Mapped[ParseStatus] = mapped_column(
        Enum(ParseStatus), default=ParseStatus.pending, nullable=False
    )
    parse_error: Mapped[str | None] = mapped_column(Text)
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    school: Mapped["School"] = relationship(back_populates="reports")
    employment_data: Mapped[list["EmploymentData"]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
