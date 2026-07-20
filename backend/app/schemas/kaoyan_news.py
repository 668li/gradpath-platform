"""考研资讯 Pydantic schemas"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class KaoyanNewsBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="标题")
    summary: Optional[str] = Field(None, max_length=500, description="摘要")
    content: Optional[str] = Field(None, description="正文内容")
    source_platform: str = Field(default="rss", description="来源平台")
    source_url: str = Field(..., description="来源链接")
    published_at: Optional[datetime] = Field(None, description="发布时间")
    category: str = Field(default="general", description="分类")
    tags: list[str] = Field(default_factory=list, description="标签")


class KaoyanNewsCreate(KaoyanNewsBase):
    """创建考研资讯"""
    pass


class KaoyanNewsUpdate(BaseModel):
    """更新考研资讯"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    summary: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = None
    source_url: Optional[str] = None
    published_at: Optional[datetime] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None


class KaoyanNewsResponse(KaoyanNewsBase):
    """考研资讯响应"""
    id: UUID
    crawled_at: datetime
    status: str = Field(..., description="审核状态")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KaoyanNewsListResponse(BaseModel):
    """考研资讯列表响应"""
    items: list[KaoyanNewsResponse]
    total: int
    page: int
    page_size: int
