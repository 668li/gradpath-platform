"""举报相关请求/响应模型 — 社区治理。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.report import ReportTargetType


class ReportCreateRequest(BaseModel):
    """提交举报。target_type + target_id 定位被举报对象。"""

    target_type: ReportTargetType
    target_id: str = Field(min_length=1, max_length=64, description="目标主键（UUID hex 字符串）")
    reason: str = Field(
        min_length=1, max_length=100, description="举报原因（如：广告/人身攻击/不实信息）"
    )
    detail: str | None = Field(default=None, max_length=2000, description="补充说明")


class ReportVO(BaseModel):
    """管理端举报列表项（枚举转字符串便于前端展示）。"""

    id: UUID
    reporter_id: UUID
    target_type: str
    target_id: str
    reason: str
    detail: str | None
    status: str
    processed_by: UUID | None
    processed_at: datetime | None
    processed_note: str | None
    created_at: datetime


class ReportListVO(BaseModel):
    total: int
    items: list[ReportVO]


class ReportProcessRequest(BaseModel):
    """管理员处理举报。

    - action=processed：举报成立 → 下架内容（可选联动封禁作者）
    - action=rejected：举报不成立
    """

    action: str = Field(pattern="^(processed|rejected)$")
    ban_author: bool = Field(
        default=False, description="action=processed 时是否同时封禁被举报对象作者"
    )
    ban_reason: str | None = Field(
        default=None, max_length=500, description="封禁原因（ban_author=true 必填）"
    )
    note: str | None = Field(default=None, max_length=500, description="处理备注（会通知举报人）")


class ReportProcessResult(BaseModel):
    report_id: UUID
    status: str
    message: str = "处理完成"
