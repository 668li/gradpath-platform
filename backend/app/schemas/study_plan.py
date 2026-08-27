"""学习计划 Schema"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StudyPlanCreate(BaseModel):
    """创建学习计划请求"""

    title: str = Field(..., min_length=1, max_length=200)
    start_date: str | None = None
    end_date: str | None = None
    subjects: list[str] | None = None
    completed: bool = False
    progress: int = Field(default=0, ge=0, le=100)


class StudyPlanUpdate(BaseModel):
    """更新学习计划请求"""

    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    subjects: list[str] | None = None
    completed: bool | None = None
    progress: int | None = Field(default=None, ge=0, le=100)


class StudyPlanResponse(BaseModel):
    """学习计划响应"""

    id: UUID
    user_id: UUID
    title: str
    start_date: str | None
    end_date: str | None
    subjects: list[str] | None
    completed: bool
    progress: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
