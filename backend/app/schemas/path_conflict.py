"""路径冲突调解 Schemas。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PathConflictOption(BaseModel):
    """单条路径选项。"""

    id: int = Field(..., description="选项索引：0=坚持现状, 1=转向推荐, 2=折中方案")
    title: str = Field(..., description="选项标题，如 '坚持现状'")
    description: str = Field(..., description="选项描述")
    pros: list[str] = Field(default_factory=list, description="优势列表")
    cons: list[str] = Field(default_factory=list, description="劣势列表")
    estimated_timeline: str = Field("", description="预计时间线")
    risk_level: str = Field("medium", description="风险等级：low / medium / high")


class PathConflictDetectResponse(BaseModel):
    """冲突检测响应 — 返回冲突摘要 + 3 条选项。"""

    conflict_id: str = Field(..., description="本次冲突检测的唯一 ID（用于后续提交选择）")
    conflict_type: str = Field(..., description="冲突类型，如 assessment_vs_current")
    has_conflict: bool = Field(..., description="是否存在冲突")
    assessment_summary: dict = Field(default_factory=dict, description="测评结果摘要")
    current_situation: dict = Field(default_factory=dict, description="用户现状摘要")
    options: list[PathConflictOption] = Field(default_factory=list, description="3 条路径选项")
    message: str = Field("", description="提示信息（无冲突时给出说明）")


class PathConflictResolveRequest(BaseModel):
    """提交用户选择的请求体。"""

    conflict_id: str = Field(..., description="detect 接口返回的 conflict_id")
    selected_option: int = Field(..., ge=0, le=2, description="用户选择的选项索引：0/1/2")
    reasoning: str = Field("", max_length=2000, description="用户选择的理由")


class PathConflictActionPlan(BaseModel):
    """行动计划结构。"""

    summary: str = Field("", description="计划摘要")
    milestones: list[dict] = Field(default_factory=list, description="里程碑列表")
    resources: list[str] = Field(default_factory=list, description="推荐资源")
    risks: list[str] = Field(default_factory=list, description="风险提示")


class PathConflictResolutionResponse(BaseModel):
    """调解记录响应 — 提交选择后或查询历史时返回。"""

    id: UUID
    user_id: UUID
    conflict_type: str
    assessment_summary: dict
    current_situation: dict
    options: list
    selected_option: int | None
    reasoning: str | None
    action_plan: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
