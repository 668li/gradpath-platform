from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应结构。"""

    items: list[T]
    total: int
    page: int
    page_size: int


class CursorPaginatedResponse(BaseModel, Generic[T]):
    """游标分页响应结构 — 避免深页 offset 性能退化。"""

    items: list[T]
    next_cursor: str | None = Field(None, description="下一页游标，null 表示已到最后一页")
    has_more: bool = Field(..., description="是否还有更多数据")
