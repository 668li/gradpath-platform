"""考研情报模型 — 院校情报、自我定位、暗知识。

考研本质是信息战。这三个模型分别解决：
1. 院校隐性信息不透明（卡学历/保护一志愿/压分/报录比）
2. 自我定位模糊（我能考上什么层次的学校）
3. "你不知道你不知道"的盲区知识
"""
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class GradSchoolIntel(UUIDMixin, TimestampMixin, Base):
    """院校情报 — 目标院校的隐性录取信息。

    核心字段对应考研学生最关心的 4 个问题：
    - 卡不卡第一学历？(background_discrimination)
    - 保护第一志愿吗？(first_choice_protection)
    - 报录比多少？真实统考名额？(admission_ratio)
    - 复试怎么考？占比多少？(retest_weight / retest_format)
    """
    __tablename__ = "grad_school_intel"
    __table_args__ = (
        Index("ix_school_intel_unique", "school_name", "major_name", unique=True),
        Index("ix_school_intel_user_school", "user_id", "school_name"),
        Index("ix_school_intel_tier_year", "school_tier", "year"),
    )

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)
    major_name: Mapped[str] = mapped_column(String(200), nullable=False)
    school_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    year: Mapped[int] = mapped_column(Integer, nullable=False, default=2026)

    # === 核心情报 ===
    # 卡第一学历程度: none / light / moderate / severe / unknown
    background_discrimination: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    # 保护第一志愿: yes / partial / no / unknown
    first_choice_protection: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    # 报录比（含推免），如 "15:1"
    admission_ratio: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 推免占比，如 "60%"
    push_ratio: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 实际统考名额（推免后剩余）
    actual_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 复试分数线
    score_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 复试占比，如 "50%"
    retest_weight: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # 复试形式描述
    retest_format: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 是否存在压分现象
    score_suppression: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    # 调剂友好度: yes / moderate / no / unknown
    transfer_friendly: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")

    # === 内部消息 ===
    insider_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SelfPositioning(UUIDMixin, TimestampMixin, Base):
    """自我定位 — 用户背景 + AI 三档推荐。

    解决"我能考上什么学校"的自我认知问题。
    AI 基于背景数据生成冲刺/稳妥/保底三档院校推荐。
    """
    __tablename__ = "self_positionings"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # === 用户背景 ===
    undergrad_tier: Mapped[str] = mapped_column(String(50), nullable=False)
    undergrad_major: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    gpa_rank: Mapped[str | None] = mapped_column(String(50), nullable=True)
    english_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    english_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    research_experience: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    awards: Mapped[str | None] = mapped_column(Text, nullable=True)
    internships: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_school: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_major: Mapped[str | None] = mapped_column(String(200), nullable=True)
    target_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    other_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    # === AI 评估结果 ===
    ai_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    reach_schools: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    target_schools: Mapped[list] = mapped_column(JSONB, default=list)
    safety_schools: Mapped[list] = mapped_column(JSONB, default=list)
    success_probability: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class DarkKnowledge(UUIDMixin, TimestampMixin, Base):
    """暗知识 — 考研全流程中"你不知道你不知道"的盲区知识。

    预填充结构化内容，按阶段分类。
    每条知识包含：核心内容 + 常见误区 + 行动建议 + 验证方法。
    """
    __tablename__ = "dark_knowledge"
    __table_args__ = (
        Index("ix_dark_knowledge_stage_sort", "stage", "sort_order"),
        Index("ix_dark_knowledge_stage_category", "stage", "category"),
    )

    # 阶段: decision / school_selection / preparation / exam / retest / transfer
    stage: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    importance: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    # 常见误区
    common_misconception: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 行动建议
    actionable_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 验证方法
    verification_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class GradYanzhaoProgram(UUIDMixin, TimestampMixin, Base):
    """研招网真实专业目录 — 院校/院系/专业/招生人数等结构化招生信息。"""

    __tablename__ = "grad_yanzhao_programs"
    __table_args__ = (
        Index("ix_yanzhao_unique", "university_name", "major_name", "year", unique=True),
    )

    university_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(200), nullable=False)
    major_name: Mapped[str] = mapped_column(String(200), nullable=False)
    degree_type: Mapped[str] = mapped_column(String(50), nullable=False)
    research_directions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    enrollment_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tuition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(50), nullable=True)
    study_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    admission_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, default=2026)
    data_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class GradScorelineRecord(UUIDMixin, TimestampMixin, Base):
    """院校真实复试分数线 — 总分/单科线及报录情况。"""

    __tablename__ = "grad_scoreline_records"
    __table_args__ = (
        Index("ix_scoreline_uni_major_year", "university_name", "major_name", "year"),
    )

    university_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    major_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    degree_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    total_score_line: Mapped[int | None] = mapped_column(Integer, nullable=True)
    politics_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    foreign_language_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    business_1_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    business_2_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrollment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    application_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adjustment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    data_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class GradAdjustmentInfo(UUIDMixin, TimestampMixin, Base):
    """研招网调剂信息 — 调剂名额、生源要求、联系方式等。"""

    __tablename__ = "grad_adjustment_info"
    __table_args__ = (
        Index("ix_adjustment_unique", "university_name", "department", "major_name", "year", unique=True),
    )

    university_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(200), nullable=False)
    major_name: Mapped[str] = mapped_column(String(200), nullable=False)
    degree_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    original_major_range: Mapped[str | None] = mapped_column(Text, nullable=True)
    adjustment_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deadline: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False, default=2025)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    data_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
