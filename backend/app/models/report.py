"""内容/用户举报模型 — 社区治理。"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class ReportTargetType(str, enum.Enum):
    """可举报的对象类型。target_id 为该对象主键（UUID hex，跨表统一字符串存储）。"""

    post = "post"  # 讨论帖
    experience_post = "experience_post"  # 经验贴
    comment = "comment"  # 评论
    qa = "qa"  # 问答
    qa_answer = "qa_answer"  # 回答
    user = "user"  # 用户（人身攻击等）


class ReportStatus(str, enum.Enum):
    pending = "pending"
    processed = "processed"  # 已处理（内容下架/封禁联动）
    rejected = "rejected"  # 举报不成立


class Report(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        # 管理端默认按状态+时间倒序拉取
        Index("ix_reports_status_created", "status", "created_at"),
        # 查同一对象被举报历史
        Index("ix_reports_target", "target_type", "target_id"),
    )

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    target_type: Mapped[ReportTargetType] = mapped_column(
        Enum(ReportTargetType), nullable=False
    )
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        nullable=False,
        default=ReportStatus.pending,
        server_default=ReportStatus.pending.value,
    )
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
