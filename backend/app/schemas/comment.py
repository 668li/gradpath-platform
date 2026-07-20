"""评论 Pydantic schemas。"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommentBase(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="评论内容")
    parent_id: Optional[UUID] = Field(None, description="父评论 ID（回复时传）")


class CommentCreate(CommentBase):
    post_id: UUID = Field(..., description="帖子 ID")


class CommentResponse(BaseModel):
    id: UUID
    post_id: UUID
    user_id: UUID
    content: str
    parent_id: Optional[UUID] = None
    like_count: int
    is_deleted: bool
    author_nickname: str = Field(default="匿名用户")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int
