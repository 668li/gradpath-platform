"""管理端用户管理 schemas — 封禁/解封/列表。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdminUserVO(BaseModel):
    """管理端用户列表项。"""

    id: UUID
    email: str
    name: str
    nickname: str | None = None
    school: str | None = None
    major: str | None = None
    graduation_year: int | None = None
    is_admin: bool = False
    status: str = "active"
    banned_at: datetime | None = None
    ban_reason: str | None = None
    created_at: datetime


class AdminUserListVO(BaseModel):
    total: int
    items: list[AdminUserVO]


class BanRequest(BaseModel):
    reason: str = Field(
        min_length=1, max_length=500, description="封禁原因（必填，会展示给被封用户）"
    )


class BanResponse(BaseModel):
    id: UUID
    status: str
    banned_at: datetime | None = None
    ban_reason: str | None = None
    message: str
