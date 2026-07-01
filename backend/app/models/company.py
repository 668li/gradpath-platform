# backend/app/models/company.py
"""公司元数据模型 — 接入外部公司基准信息，供 AI 决策指导与查询接口使用。"""
import enum

from sqlalchemy import Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class CompanySize(str, enum.Enum):
    """公司规模枚举（按员工人数划分）。"""

    startup = "startup"   # <50
    small = "small"       # 50-200
    medium = "medium"     # 200-2000
    large = "large"       # 2000-10000
    giant = "giant"       # >10000


class Company(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    industry: Mapped[str] = mapped_column(String(50), nullable=False)
    size: Mapped[CompanySize] = mapped_column(Enum(CompanySize), nullable=False)
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    headquarters: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
