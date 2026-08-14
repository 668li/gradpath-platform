"""用户屏蔽相关响应模型 — 社区治理。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BlockedUserVO(BaseModel):
    """屏蔽列表项 — 被屏蔽用户的公开信息。"""

    blocked_id: UUID
    name: str
    nickname: str | None = None
    school: str | None = None
    major: str | None = None
    blocked_at: datetime


class BlockListVO(BaseModel):
    total: int
    items: list[BlockedUserVO]


class BlockResult(BaseModel):
    blocked_id: UUID
    message: str = "操作成功"
