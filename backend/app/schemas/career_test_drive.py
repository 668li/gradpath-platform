# backend/app/schemas/career_test_drive.py
"""职业试驾 Pydantic Schema。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TimeBlock(BaseModel):
    """一日体验中的单个时间段。"""

    time: str  # "08:30"
    activity: str  # "晨会"
    description: str  # 详细描述
    emotion: str  # "专注" / "疲惫" / "兴奋"


class CareerTestDriveCreate(BaseModel):
    """试驾生成请求。"""

    path_type: str = Field(..., description="路径类型: kaoyan/employment/civil_service")
    target_role: str = Field(..., min_length=1, max_length=100, description="目标角色")


class CareerTestDriveResponse(BaseModel):
    """试驾响应 — 展开后的完整一日体验。"""

    id: UUID
    path_type: str
    target_role: str
    experience_content: list[TimeBlock]
    summary: str
    pros: list[str]
    cons: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}
