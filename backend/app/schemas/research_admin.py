"""管理员外部调研 API 的 Pydantic Schema。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BilibiliResearchRequest(BaseModel):
    """触发 B站调研请求。"""

    keyword: str = Field(..., min_length=1, description="搜索关键词")
    pages: int = Field(1, ge=1, le=10, description="抓取页数")
    auto_approve: bool = Field(False, description="是否自动审核通过")


class RssResearchRequest(BaseModel):
    """触发 RSS 调研请求。"""

    feeds: list[str] | None = Field(None, description="RSS 订阅源 URL 列表")
    keywords: list[str] | None = Field(None, description="标题/摘要关键词过滤")
    auto_approve: bool = Field(False, description="是否自动审核通过")


class ResearchTriggerResponse(BaseModel):
    """调研触发响应。"""

    status: str = Field(..., description="执行状态")
    fetched: int = Field(..., description="抓取原始条数")
    stored: int = Field(..., description="导入数据库条数")
    pending: int = Field(..., description="待审核条数")


class ResearchApproveRequest(BaseModel):
    """审核/拒绝请求。"""

    item_type: str = Field(..., pattern="^(experience|news)$", description="项目类型")


class ResearchPendingItem(BaseModel):
    """待审核外部调研项目。"""

    id: UUID
    title: str
    summary: str | None
    source_platform: str
    source_url: str | None
    status: str
    item_type: str  # experience / news
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResearchPendingListResponse(BaseModel):
    """待审核列表响应。"""

    items: list[ResearchPendingItem]
    total: int
    page: int
    page_size: int
