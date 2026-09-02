# backend/app/models/assessment.py
"""职业测评模型 — 霍兰德职业兴趣测评等。

记录用户每次测评的答案、结果编码、结果摘要与推荐方向，供个性化推荐与规划生成使用。
"""

from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class Assessment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "assessments"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "holland" | "mbti"
    answers: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"q1": "A", "q2": "C", ...}
    result_code: Mapped[str] = mapped_column(String(20), nullable=False)  # 如 "RIA"（top 3 维度）
    result_summary: Mapped[str] = mapped_column(Text, nullable=False)  # 中文描述
    recommended_directions: Mapped[list] = mapped_column(
        JSONB, nullable=False
    )  # ["后端开发", "数据分析", ...]
    # 维度分（各测评的真实维度得分；大五为均分 dict[str,float]，其余为计数）。
    # 旧行可能为 NULL，读取时由 answers 实时回填（见 assessment.py 的 _to_response）。
    scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # {"R": 9, "I": 7, ...}
