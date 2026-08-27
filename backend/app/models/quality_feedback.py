"""质量分反馈模型 — 用户对质量分/证据链的评分反馈（Phase I 反馈闭环）。

用户对某条经验贴/资讯的质量分点「有帮助/不准确」并可选附原因。
P0 仅采集存储：同用户对同一条目只保留最新一次反馈（可切换），
管理端统计/处理留 P1。
"""

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import GUID, TimestampMixin, UUIDMixin


class QualityFeedbackTargetType(str, enum.Enum):
    """可反馈质量分的对象类型。target_id 为该对象主键（UUID hex，跨表统一字符串存储）。"""

    experience_post = "experience_post"  # 经验贴
    kaoyan_news = "kaoyan_news"  # 考研资讯


class QualityFeedbackType(str, enum.Enum):
    helpful = "helpful"  # 有帮助（认可质量分/证据链）
    unhelpful = "unhelpful"  # 不准确（认为质量分或证据有误）


class QualityFeedback(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "quality_feedback"
    __table_args__ = (
        # 同用户同条目只留最新一条反馈（可切换）——幂等 upsert 依据
        UniqueConstraint(
            "user_id", "target_type", "target_id", name="uq_quality_feedback_user_target"
        ),
        # 管理端按目标条目聚合查询（P1 统计预留）
        Index("ix_quality_feedback_target", "target_type", "target_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    target_type: Mapped[QualityFeedbackTargetType] = mapped_column(
        Enum(QualityFeedbackTargetType), nullable=False
    )
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    feedback_type: Mapped[QualityFeedbackType] = mapped_column(
        Enum(QualityFeedbackType), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 选填原因
