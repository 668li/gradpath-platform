"""首次诊断模型 — 用户入门 5 分钟职业诊断。

新用户首次登录后完成 4 步诊断（基本信息 / 目标方向 / 自我评估 / 提交），
AI 基于答案生成个性化诊断 + 推荐路径，作为后续 AI 个性化的初始基线。
"""
import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, JSONB, TimestampMixin, UUIDMixin


class OnboardingStatus(str, enum.Enum):
    """诊断状态 — 跟踪诊断流程进度。"""
    in_progress = "in_progress"   # 进行中（已保存答案，未生成诊断）
    completed = "completed"       # 已完成（AI 诊断已生成）
    skipped = "skipped"           # 已跳过（用户选择跳过）


class UserOnboarding(UUIDMixin, TimestampMixin, Base):
    """用户首次诊断记录 — 一对一关系（每用户最多一条有效记录）。

    设计：
    - self_assessment 存储用户自我评估的原始答案（JSONB）
    - ai_diagnosis 存储 AI 生成的诊断文本
    - recommended_path 存储 AI 推荐的行动路径（结构化 JSONB）
    - completed_at 记录完成时间，用于触发后续流程
    """
    __tablename__ = "user_onboardings"

    user_id: Mapped[UUID] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # === 用户输入 ===
    current_stage: Mapped[str] = mapped_column(String(50), nullable=False)
    # 目标方向: employment / postgrad / civil_service / abroad / phd / startup / gap_year
    target_direction: Mapped[str] = mapped_column(String(50), nullable=False)
    target_industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 自我评估原始答案，结构由前端 4 步表单决定
    self_assessment: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # === AI 生成结果 ===
    status: Mapped[OnboardingStatus] = mapped_column(
        Enum(OnboardingStatus), nullable=False, default=OnboardingStatus.in_progress
    )
    ai_diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 推荐路径：结构化 JSON，如 {"short_term": [...], "mid_term": [...], "long_term": [...]}
    recommended_path: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # AI 识别的关键风险/优势点
    key_insights: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
