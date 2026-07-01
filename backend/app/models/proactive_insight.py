"""AI 主动洞察模型 — 跨数据模式识别，主动生成非显而易见的洞察。

不同于 reactive 的成长洞察（用户请求时生成），主动洞察是系统主动分析
用户数据模式后生成的，展示在看板上提醒用户注意。
"""
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import JSONB, TimestampMixin, UUIDMixin


class ProactiveInsight(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "proactive_insights"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 洞察类型: "pattern" | "reminder" | "celebration" | "warning" | "suggestion"
    insight_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # 标题（一句话概括）
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 详细内容
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # AI 建议的下一步行动
    action_suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 优先级 1-5（5 最高）
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # 关联数据（如涉及的决策 ID、事件 ID 等）
    related_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # 是否已读
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
