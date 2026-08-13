"""失败案例库 Pydantic schemas — 匿名分享真实失败叙事。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# 路径与阶段白名单（服务层会做二次校验）
PATH_TYPES = {"kaoyan", "civil_service", "employment", "study_abroad"}
STAGES = {"preparation", "interview", "final_year1", "year2_plus"}


class FailureCaseCreate(BaseModel):
    """用户提交的失败案例。"""
    author_role: str = Field(..., min_length=1, max_length=50, description="作者身份，如 在校生/毕业生/工作3年内")
    path_type: str = Field(..., max_length=50, description="路径：kaoyan/civil_service/employment/study_abroad")
    stage: str = Field(..., max_length=50, description="阶段：preparation/interview/final_year1/year2_plus")
    title: str = Field(..., min_length=1, max_length=200, description="标题")
    story: str = Field(..., min_length=1, max_length=20000, description="第一人称叙事")
    lessons: list[str] = Field(default_factory=list, description="教训列表")
    regrets: list[str] = Field(default_factory=list, description="后悔的事")
    what_would_i_do: str = Field(..., min_length=1, max_length=10000, description="如果重来会怎么做")


class FailureCaseResponse(BaseModel):
    """失败案例响应 — 不含 user_id（匿名设计）。"""
    id: UUID
    author_role: str
    path_type: str
    stage: str
    title: str
    story: str
    lessons: list[str]
    regrets: list[str]
    what_would_i_do: str
    helpful_count: int = Field(default=0)
    view_count: int = Field(default=0)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FailureCaseListResponse(BaseModel):
    """失败案例列表响应。"""
    items: list[FailureCaseResponse]
    total: int
    page: int
    page_size: int


class FailureCaseStatsResponse(BaseModel):
    """失败案例统计响应。"""
    total: int
    by_path: dict[str, int] = Field(default_factory=dict)
    by_stage: dict[str, int] = Field(default_factory=dict)
