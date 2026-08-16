"""质量分反馈 Pydantic schemas（Phase I 反馈闭环）。"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.quality_feedback import (
    QualityFeedbackTargetType,
    QualityFeedbackType,
)


class QualityFeedbackCreate(BaseModel):
    """创建/更新质量反馈（upsert：同用户同条目只留最新一条）。

    target_id 为经验贴/资讯主键（UUID 字符串，hex 或带连字符均可）。
    reason 选填；反馈类型可随时切换（如 👎 → 👍，会替换旧反馈）。
    """

    target_type: QualityFeedbackTargetType = Field(
        ..., description="目标类型：experience_post / kaoyan_news"
    )
    target_id: str = Field(
        ..., min_length=32, max_length=64, description="目标条目主键（UUID 字符串）"
    )
    feedback_type: QualityFeedbackType = Field(
        ..., description="反馈类型：helpful / unhelpful"
    )
    reason: Optional[str] = Field(
        None, max_length=200, description="选填原因（如证据有误/质量分不合理）"
    )


class QualityFeedbackResponse(BaseModel):
    id: UUID
    target_type: QualityFeedbackTargetType
    target_id: str
    feedback_type: QualityFeedbackType
    reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
