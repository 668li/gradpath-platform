"""求职作战室模型 — 公司情报 + 求职定位 + 求职暗知识。

借鉴考研作战室的三模型结构，解决求职场景的信息不对称问题。
"""
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class CompanyIntel(UUIDMixin, TimestampMixin, Base):
    """公司情报 — AI 生成的结构化公司/岗位情报画像。"""
    __tablename__ = "career_company_intel"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position_name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[str] = mapped_column(String(100), nullable=False, default="")

    # 核心情报字段（枚举式，便于前端颜色映射）
    overtime_intensity: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    layoff_risk: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    promotion_outlook: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    education_barrier: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    salary_honesty: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    culture_fit: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")

    # 数据字段
    salary_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    actual_salary: Mapped[str | None] = mapped_column(String(100), nullable=True)
    interview_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    interview_rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turnover_rate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    growth_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 内部消息
    insider_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # 元信息
    data_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CareerPositioning(UUIDMixin, TimestampMixin, Base):
    """求职定位 — 用户背景 + AI 评估 + 三档公司推荐。"""
    __tablename__ = "career_positionings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 用户背景
    education_level: Mapped[str] = mapped_column(String(50), nullable=False)
    school_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    major: Mapped[str | None] = mapped_column(String(200), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gpa: Mapped[float | None] = mapped_column(nullable=True)
    internships: Mapped[str | None] = mapped_column(Text, nullable=True)
    skills: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    competitions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    projects: Mapped[str | None] = mapped_column(Text, nullable=True)
    certifications: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_position: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    salary_expectation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    other_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI 生成结果
    ai_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitiveness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reach_companies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    target_companies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    safety_companies: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    salary_estimate: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skill_gaps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    risk_warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class CareerDarkKnowledge(UUIDMixin, TimestampMixin, Base):
    """求职暗知识 — 预填充的求职盲区知识。"""
    __tablename__ = "career_dark_knowledge"

    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    common_misconception: Mapped[str | None] = mapped_column(Text, nullable=True)
    actionable_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    verification_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
