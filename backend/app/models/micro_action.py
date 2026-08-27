"""7天微行动模型 — 7 天低成本探索任务。

核心哲学：不替用户决定，而是让用户通过 7 天低成本行动自己发现答案。
每天一个具体任务（调研/访谈/实践/复盘），15-30 分钟可完成，
第 7 天生成"自我发现报告"。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class MicroActionPlan(UUIDMixin, TimestampMixin, Base):
    """一个 7 天微行动计划，对应一条职业路径探索。"""

    __tablename__ = "micro_action_plans"

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 目标路径：kaoyan/employment/civil_service
    target_path: Mapped[str] = mapped_column(String(50), nullable=False)
    # 可选，具体岗位/院校/职位
    target_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # active / completed / abandoned
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    # 计划开始时间
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # 计划完成时间
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 第 7 天生成的自我发现报告
    self_discovery_report: Mapped[str | None] = mapped_column(Text, nullable=True)


class MicroActionTask(UUIDMixin, TimestampMixin, Base):
    """计划下的单日任务（1-7 天）。"""

    __tablename__ = "micro_action_tasks"

    plan_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("micro_action_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 1-7
    day_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # research / interview / practice / reflect
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    # pending / completed / skipped
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # 任务完成时间
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 用户完成任务后的记录
    user_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI 生成的洞察（"从你的记录中，我发现..."）
    insight: Mapped[str | None] = mapped_column(Text, nullable=True)
