"""讨论帖的 Pydantic Schema 定义。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PostCreate(BaseModel):
    topic_type: str
    topic_key: str = Field(..., max_length=500)
    content: str = Field(..., min_length=1, max_length=2000)
    parent_id: str | None = None


class PostUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class PostResponse(BaseModel):
    id: str
    topic_type: str
    topic_key: str
    content: str
    author_id: str
    author_name: str
    parent_id: str | None = None
    created_at: datetime
    updated_at: datetime
    replies: list["PostResponse"] = []

    model_config = {"from_attributes": True}

    @field_validator("id", "author_id", "parent_id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        if v is None:
            return v
        return str(v) if hasattr(v, "hex") else v

    @field_validator("topic_type", mode="before")
    @classmethod
    def convert_enum(cls, v):
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)


class PostListResponse(BaseModel):
    items: list[PostResponse]
    total: int
    page: int
    page_size: int
