"""通知的 Pydantic Schema 定义。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    content: str
    read: bool
    archived: bool = False
    archived_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v

    @field_validator("type", mode="before")
    @classmethod
    def convert_enum(cls, v):
        return v.value if hasattr(v, "value") else str(v)


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int


class NotificationCountResponse(BaseModel):
    unread_count: int


class NotificationCreate(BaseModel):
    user_id: str
    type: str = "system"
    title: str
    content: str = ""


class NotificationArchiveResponse(BaseModel):
    """归档操作响应。"""
    message: str
    archived_count: int = 0
