"""人生设计引擎模型 — AI Life Design 七步法落地。

将模糊的人生焦虑转化为结构化的行动系统：
人生审计 → 愿景构建 → 90天冲刺(季度聚焦) → 周复盘 → 季度回顾

每个 sprint 代表一个季度，用户选择一个主攻领域集中投入，
其余领域进入维护模式（守住底线不恶化）。
"""
from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class LifeDesignSprint(UUIDMixin, TimestampMixin, Base):
    """90 天冲刺 — 季度聚焦一个主攻领域。"""
    __tablename__ = "life_design_sprints"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 冲刺名称（如 "2026 Q3: 技术能力突破"）
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # 主攻领域: career / finance / health / relationships / growth / fun / environment / spirituality
    primary_domain: Mapped[str] = mapped_column(String(30), nullable=False)
    # 维护领域列表（守住底线，不优化）
    maintenance_domains: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 开始日期（通常为季度第一天）
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 结束日期（通常 90 天后）
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # 状态: planned / active / completed / abandoned
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")
    # 3 个 SMART 目标（主攻领域的具体目标）
    goals: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 愿景声明（2-3 年理想生活描述）
    vision_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 审计摘要（人生审计的关键发现）
    audit_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 审计问答记录 [{question, answer}]
    audit_qa: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # 季度回顾笔记
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI 季度回顾分析
    ai_review: Mapped[str | None] = mapped_column(Text, nullable=True)


class WeeklyReview(UUIDMixin, TimestampMixin, Base):
    """周复盘 — 每周回顾目标执行情况，AI 辅助分析。"""
    __tablename__ = "weekly_reviews"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sprint_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("life_design_sprints.id", ondelete="SET NULL"), nullable=True
    )
    # 周开始日期（周一）
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    # 本周计划做了什么
    planned_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 实际做了什么
    actual_actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 什么有效
    what_worked: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 什么没效
    what_didnt_work: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 下周调整方向
    next_week_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 能量水平 1-5
    energy_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # AI 分析
    ai_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
