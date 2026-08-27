"""审核队列（t_review_queue_item）管理 API 的 Pydantic Schema。

审核链路统一走新队列后（系统设计主线 c / F9），管理员在
/admin/research-queue 对采集条目执行 通过/驳回/标记重复。
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ResearchQueueItemVO(BaseModel):
    """审核队列条目 + 关联的 t_external_research_item 详情。"""

    queue_id: int
    item_type: str  # external_research
    ref_item_id: int
    biz_req_no: str
    source_url: str
    review_status: str  # PENDING / APPROVED / REJECTED / DUPLICATED
    reject_reason: str | None
    reviewed_by: str | None
    reviewed_time: datetime | None
    created_time: datetime

    # === t_external_research_item 关联详情 ===
    title: str
    content: str
    crawler_name: str
    source_platform: str
    credibility: str  # official_verified / user_reported / model_inferred
    external_meta: dict | None

    model_config = ConfigDict(from_attributes=True)


class ResearchQueueListResponse(BaseModel):
    """待审核列表响应。"""

    items: list[ResearchQueueItemVO]
    total: int
    page: int
    page_size: int


class QueueApproveRequest(BaseModel):
    """审核通过请求（管理员显式确认）。"""

    note: str | None = Field(None, max_length=200, description="审核备注（可选）")


class QueueRejectRequest(BaseModel):
    """驳回请求。"""

    reject_reason: str | None = Field(
        None, max_length=500, description="驳回原因（可选但建议填写）"
    )


class QueueDuplicateRequest(BaseModel):
    """标记重复请求。"""

    duplicate_of: str | None = Field(
        None, max_length=500, description="重复来源 URL 或说明（可选）"
    )


class QueueActionResponse(BaseModel):
    """审核操作响应。"""

    message: str
    queue_id: int
    review_status: str
    ref_item_id: int
    promoted: int = Field(0, description="审核通过时落业务表的条数（0/1）")
