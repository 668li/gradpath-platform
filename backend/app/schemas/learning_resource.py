"""学习资源 Schema"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LearningResourceCreate(BaseModel):
    """创建学习资源请求"""

    title: str = Field(..., min_length=1, max_length=200)
    url: str | None = None
    resource_type: str = Field(..., pattern="^(video|book|course|article)$")
    subject: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    description: str | None = None
    tags: list[str] | None = None
    rating: int = Field(default=0, ge=0, le=5)
    is_free: bool = True


class LearningResourceUpdate(BaseModel):
    """更新学习资源请求"""

    title: str | None = None
    url: str | None = None
    resource_type: str | None = None
    subject: str | None = None
    difficulty: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    rating: int | None = Field(default=None, ge=0, le=5)
    is_free: bool | None = None


class LearningResourceResponse(BaseModel):
    """学习资源响应"""

    id: UUID
    user_id: UUID
    title: str
    url: str | None
    resource_type: str
    subject: str
    difficulty: str
    description: str | None
    tags: list[str] | None
    rating: int
    is_free: bool
    view_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
