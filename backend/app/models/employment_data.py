# backend/app/models/employment_data.py
import enum
from uuid import UUID

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


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

    # report_id 允许为空：公开报告导入（reports 爬虫）不依赖 ReportRecord，
    # 直接使用 school_name + year + major_category 维护记录。
    report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("report_records.id"), nullable=True
    )
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

    # === 公开报告导入扩展字段（reports 爬虫使用，独立于 ReportRecord 流程）===
    user_id: Mapped[UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    school_name: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    school_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 985 / 211 / 普通本科
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    major_category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 工学/经济学/理学 等
    unemployment_rate: Mapped[float | None] = mapped_column(Float)
    top_employers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # 前 5 雇主列表
    average_salary: Mapped[float | None] = mapped_column(Float)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
