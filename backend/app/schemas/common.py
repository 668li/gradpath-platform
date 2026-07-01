from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """通用分页响应结构。"""

    items: list[T]
    total: int
    page: int
    page_size: int
