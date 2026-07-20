"""收藏的 Pydantic Schema 定义。"""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.bookmark import BookmarkTargetType


class BookmarkCreate(BaseModel):
    target_type: BookmarkTargetType = Field(..., description="收藏目标类型")
    target_id: str = Field(..., max_length=500)


class BookmarkResponse(BaseModel):
    id: str
    target_type: str
    target_id: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v

    @field_validator("target_type", mode="before")
    @classmethod
    def convert_enum(cls, v):
        return v.value if hasattr(v, "value") else str(v)


class BookmarkListResponse(BaseModel):
    items: list[BookmarkResponse]
    total: int
