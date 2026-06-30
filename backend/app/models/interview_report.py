# backend/app/models/interview_report.py
"""公司面试经验报告模型 — 用户匿名分享面试经历，聚合后展示"这家公司面试官看重什么"。"""
import enum
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class InterviewDimension(str, enum.Enum):
    algorithm = "algorithm"
    system_design = "system_design"
    project_depth = "project_depth"
    culture_fit = "culture_fit"
    communication = "communication"
    domain_knowledge = "domain"
    behavior = "behavior"


class InterviewResult(str, enum.Enum):
    offer = "offer"
    rejected = "rejected"
    pending = "pending"


class InterviewReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "interview_reports"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "company", "position", "interview_year",
            name="uq_user_company_pos_year",
        ),
    )

    community_report_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("community_reports.id"), nullable=True
    )
    company: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(50))
    interview_year: Mapped[int] = mapped_column(Integer, nullable=False)
    rounds: Mapped[int | None] = mapped_column(Integer)
    result: Mapped[InterviewResult] = mapped_column(
        Enum(InterviewResult), default=InterviewResult.pending, nullable=False
    )
    dimensions: Mapped[list] = mapped_column(JSONB, default=list)
    difficulty: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
