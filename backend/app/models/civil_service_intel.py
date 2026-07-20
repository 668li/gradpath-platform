"""考公作战室模型 — 岗位情报 + 考公定位 + 考公暗知识。

解决考公/体制内就业的信息不对称：岗位选择、地区待遇、晋升前景、萝卜坑识别、政审体检暗坑。
"""
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class PostIntel(UUIDMixin, TimestampMixin, Base):
    """岗位情报 — AI 生成的结构化考公岗位情报画像。"""
    __tablename__ = "civil_service_post_intel"

    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(200), nullable=False)
    post_name: Mapped[str] = mapped_column(String(200), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False, default="")

    # 核心情报字段
    real_competition: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    treatment_level: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    promotion_speed: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    workload: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    radish_post: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    service_period: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")

    # 数据字段
    admission_ratio: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cutoff_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_estimate: Mapped[str | None] = mapped_column(String(100), nullable=True)
    housing_fund: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bonus_info: Mapped[str | None] = mapped_column(String(200), nullable=True)
    department_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    work_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 内部消息
    insider_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    # 元信息
    data_sources: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CivilServicePositioning(UUIDMixin, TimestampMixin, Base):
    """考公定位 — 用户背景 + AI 评估 + 三档岗位推荐。"""
    __tablename__ = "civil_service_positionings"

    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 用户背景
    education_level: Mapped[str] = mapped_column(String(50), nullable=False)
    school_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    major: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_party_member: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    student_leader: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_honors: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_fresh_graduate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    target_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    family_background: Mapped[str | None] = mapped_column(String(50), nullable=True)
    other_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    # AI 生成结果
    ai_assessment: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitiveness_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eligible_for_xuandiao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reach_posts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    target_posts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    safety_posts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preparation_timeline: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class CivilServiceDarkKnowledge(UUIDMixin, TimestampMixin, Base):
    """考公暗知识 — 预填充的考公盲区知识。"""
    __tablename__ = "civil_service_dark_knowledge"

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
