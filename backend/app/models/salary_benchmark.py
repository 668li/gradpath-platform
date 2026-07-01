# backend/app/models/salary_benchmark.py
"""薪资基准模型 — 外部市场薪资数据，供 AI 决策指导与查询接口使用。"""
import enum

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class ExperienceLevel(str, enum.Enum):
    """工作经验级别枚举。"""

    entry = "entry"       # 应届/0年
    junior = "junior"     # 1-3年
    mid = "mid"           # 3-5年
    senior = "senior"     # 5-10年
    lead = "lead"         # 10年+


class SalaryBenchmark(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "salary_benchmarks"

    company: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    position: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    experience_level: Mapped[ExperienceLevel] = mapped_column(
        Enum(ExperienceLevel), nullable=False
    )
    salary_min: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_median: Mapped[int] = mapped_column(Integer, nullable=False)
    salary_max: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
