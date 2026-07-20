"""Outcome Report (上岸报告) — 用户报告考试/求职结果，驱动数据飞轮。"""
import enum
from uuid import UUID

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class OutcomeType(str, enum.Enum):
    grad_civil_career = "grad_civil_career"  # 考研/考公/求职上岸
    adjustment = "adjustment"  # 调剂
    failed = "failed"  # 未上岸


class AdmissionPath(str, enum.Enum):
    normal = "normal"
    adjustment = "adjustment"
    transfer = "transfer"


class OutcomeReport(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "outcome_reports"
    __table_args__ = (
        {"comment": "上岸报告 — 闭环数据飞轮的核心表"},
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True,
    )
    outcome_type: Mapped[OutcomeType] = mapped_column(
        Enum(OutcomeType), nullable=False, index=True,
    )
    target_school: Mapped[str | None] = mapped_column(String(200))
    target_major: Mapped[str | None] = mapped_column(String(200))
    actual_school: Mapped[str | None] = mapped_column(String(200))
    actual_major: Mapped[str | None] = mapped_column(String(200))
    score_total: Mapped[int | None] = mapped_column(Integer)
    score_politics: Mapped[int | None] = mapped_column(Integer)
    score_english: Mapped[int | None] = mapped_column(Integer)
    score_major1: Mapped[int | None] = mapped_column(Integer)
    score_major2: Mapped[int | None] = mapped_column(Integer)
    admission_path: Mapped[AdmissionPath] = mapped_column(
        Enum(AdmissionPath), default=AdmissionPath.normal,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    confidence_before: Mapped[float | None] = mapped_column(Float)
    satisfaction_after: Mapped[int | None] = mapped_column(Integer)
    what_i_would_do_differently: Mapped[str | None] = mapped_column(Text)
    advice_for_others: Mapped[str | None] = mapped_column(Text)
    is_public: Mapped[str] = mapped_column(String(10), default="private")
