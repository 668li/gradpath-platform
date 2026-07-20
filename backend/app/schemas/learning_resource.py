"""学习资源 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class LearningResourceCreate(BaseModel):
    """创建学习资源请求"""
    title: str = Field(..., min_length=1, max_length=200)
    url: Optional[str] = None
    resource_type: str = Field(..., pattern="^(video|book|course|article)$")
    subject: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(..., pattern="^(beginner|intermediate|advanced)$")
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    rating: int = Field(default=0, ge=0, le=5)
    is_free: bool = True


class LearningResourceUpdate(BaseModel):
    """更新学习资源请求"""
    title: Optional[str] = None
    url: Optional[str] = None
    resource_type: Optional[str] = None
    subject: Optional[str] = None
    difficulty: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    rating: Optional[int] = Field(default=None, ge=0, le=5)
    is_free: Optional[bool] = None


class LearningResourceResponse(BaseModel):
    """学习资源响应"""
    id: UUID
    user_id: UUID
    title: str
    url: Optional[str]
    resource_type: str
    subject: str
    difficulty: str
    description: Optional[str]
    tags: Optional[list[str]]
    rating: int
    is_free: bool
    view_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
