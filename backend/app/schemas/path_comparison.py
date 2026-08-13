"""多路径 What-If 对比 Schemas。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PathInput(BaseModel):
    """单条待对比路径输入。"""

    path_type: str = Field(..., description="路径类型，如 kaoyan/employment/civil_service")
    target_role: str = Field(..., min_length=1, max_length=100, description="目标角色，如 '后端开发'")


class PathMetrics(BaseModel):
    """单条路径的量化指标。"""

    path_type: str = Field(..., description="路径类型")
    target_role: str = Field(..., description="目标角色")
    income_1y: str = Field(..., description="1 年预期收入区间，如 '10-15万'")
    income_3y: str = Field(..., description="3 年预期收入区间")
    income_5y: str = Field(..., description="5 年预期收入区间")
    risk_level: str = Field(..., description="风险等级：low / medium / high")
    risk_description: str = Field(..., description="风险说明")
    growth_score: int = Field(..., ge=1, le=10, description="成长性评分 1-10")
    time_cost_months: int = Field(..., ge=0, description="准备时间（月）")
    match_score: int = Field(..., ge=0, le=100, description="与用户画像匹配度 0-100")
    match_description: str = Field(..., description="匹配度说明")
    pros: list[str] = Field(default_factory=list, description="优势列表")
    cons: list[str] = Field(default_factory=list, description="劣势列表")

    @field_validator("risk_level")
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        if v not in ("low", "medium", "high"):
            raise ValueError("risk_level must be one of: low, medium, high")
        return v


class ComparisonRequest(BaseModel):
    """对比请求体 — 2-3 条路径。"""

    paths: list[PathInput] = Field(..., description="待对比路径列表")

    @field_validator("paths")
    @classmethod
    def validate_paths(cls, v: list[PathInput]) -> list[PathInput]:
        if len(v) < 2 or len(v) > 3:
            raise ValueError("paths must contain between 2 and 3 items")
        return v


class ComparisonResponse(BaseModel):
    """对比响应体。"""

    id: str = Field(..., description="对比记录 ID")
    metrics: list[PathMetrics] = Field(..., description="各路径的量化指标")
    recommendation: str = Field(..., description="综合建议（自然语言）")
    created_at: datetime = Field(..., description="创建时间")

    model_config = {"from_attributes": True}


class PathComparisonRecord(ComparisonResponse):
    """完整对比记录（含用户 ID），用于内部传递。"""

    user_id: UUID
