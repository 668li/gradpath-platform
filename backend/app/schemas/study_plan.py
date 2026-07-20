"""学习计划 Schema"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class StudyPlanCreate(BaseModel):
    """创建学习计划请求"""
    title: str = Field(..., min_length=1, max_length=200)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    subjects: Optional[list[str]] = None
    completed: bool = False
    progress: int = Field(default=0, ge=0, le=100)


class StudyPlanUpdate(BaseModel):
    """更新学习计划请求"""
    title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    subjects: Optional[list[str]] = None
    completed: Optional[bool] = None
    progress: Optional[int] = Field(default=None, ge=0, le=100)


class StudyPlanResponse(BaseModel):
    """学习计划响应"""
    id: UUID
    user_id: UUID
    title: str
    start_date: Optional[str]
    end_date: Optional[str]
    subjects: Optional[list[str]]
    completed: bool
    progress: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
