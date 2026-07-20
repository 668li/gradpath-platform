# backend/app/models/school.py
from sqlalchemy import Index, String, Text, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin


class School(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "schools"
    __table_args__ = (
        Index("ix_school_province_level", "province", "level"),
        {"info": "院校表 — 存储院校基础信息。"},
    )

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    code: Mapped[str | None] = mapped_column(String(10))
    report_index_url: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(String(20))
    level: Mapped[str | None] = mapped_column(String(20))  # 985/211/双一流/普通
    
    # 增强字段
    ranking: Mapped[int | None] = mapped_column(Integer)  # 全国排名
    key_majors: Mapped[dict | None] = mapped_column(JSON)  # 优势专业列表
    employment_rate: Mapped[float | None] = mapped_column(Float)  # 就业率(%)
    grad_school_rate: Mapped[float | None] = mapped_column(Float)  # 考研率(%)
    abroad_rate: Mapped[float | None] = mapped_column(Float)  # 出国率(%)

    reports: Mapped[list["ReportRecord"]] = relationship(back_populates="school")
