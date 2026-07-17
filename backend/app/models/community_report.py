# backend/app/models/community_report.py
"""社区毕业去向报告模型 — 用户匿名提交毕业去向，系统聚合后展示"同类人去了哪"。"""
import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin
from app.models.employment_data import Degree


class DestinationType(str, enum.Enum):
    employment = "employment"
    further_study = "further_study"
    civil_service = "civil_service"
    abroad = "abroad"
    startup = "startup"
    gap_year = "gap_year"


class SalaryRange(str, enum.Enum):
    below_8k = "below_8k"
    r8k_15k = "8k_15k"
    r15k_25k = "15k_25k"
    r25k_50k = "25k_50k"
    above_50k = "above_50k"
    prefer_not = "prefer_not"


class CommunityReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "community_reports"
    # 聚合查询高频字段添加索引：
    # - school_name/major/graduation_year：community_service 聚合过滤条件
    # - destination_type：group by 去向类型分布
    # - user_id 已在 UniqueConstraint 中自动索引
    __table_args__ = (
        UniqueConstraint("user_id", "graduation_year", name="uq_user_year"),
    )

    school_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    major: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    graduation_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    degree: Mapped[Degree] = mapped_column(Enum(Degree), default=Degree.bachelor, nullable=False)
    destination_type: Mapped[DestinationType] = mapped_column(Enum(DestinationType), nullable=False, index=True)
    employer: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(50))
    industry: Mapped[str | None] = mapped_column(String(50))
    salary_range: Mapped[SalaryRange | None] = mapped_column(Enum(SalaryRange))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
