# backend/app/models/employment_data.py
import enum
from uuid import UUID

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class Degree(str, enum.Enum):
    bachelor = "bachelor"
    master = "master"
    phd = "phd"
    all = "all"


class EmploymentData(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "employment_data"
    __table_args__ = (
        UniqueConstraint("report_id", "major", "degree", name="uq_report_major_degree"),
    )

    report_id: Mapped[UUID] = mapped_column(ForeignKey("report_records.id"), nullable=False)
    major: Mapped[str] = mapped_column(String(200), nullable=False)
    degree: Mapped[Degree] = mapped_column(Enum(Degree), default=Degree.all, nullable=False)
    total_graduates: Mapped[int | None] = mapped_column(Integer)

    employment_rate: Mapped[float | None] = mapped_column(Float)
    further_study_rate: Mapped[float | None] = mapped_column(Float)
    civil_service_rate: Mapped[float | None] = mapped_column(Float)
    abroad_rate: Mapped[float | None] = mapped_column(Float)
    startup_rate: Mapped[float | None] = mapped_column(Float)
    gap_year_rate: Mapped[float | None] = mapped_column(Float)

    employer_ranking: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    industry_distribution: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    destination_region: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    school_for_further_study: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    report: Mapped["ReportRecord"] = relationship(back_populates="employment_data")
