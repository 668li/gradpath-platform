"""报考条件账本 Pydantic schemas"""

from pydantic import BaseModel, Field


class ConditionItem(BaseModel):
    """一条报考条件 — 由 gwy_position 行规则生成。"""

    key: str = Field(..., description="条件键，如 education / major / cert_0")
    label: str = Field(..., description="条件名称，如 学历要求")
    required: str = Field(..., description="职位表原文要求")
    source_field: str = Field(..., description="溯源：来自职位表的哪个字段")


class ConditionProgress(BaseModel):
    """条件完成度 — 北极星指标「条件完成率」的职位级视图。"""

    total: int
    met: int
    in_progress: int
    unmet: int
    rate: float = Field(..., description="完成率百分比 0-100")


class ConditionChecklistResponse(BaseModel):
    """目标职位条件清单 + 用户核对状态 + 完成度。"""

    position_id: str
    position_code: str
    position_name: str | None = None
    dept_name: str | None = None
    year: int
    exam_source: str = Field("national", description="national=国考 / province=省考")
    conditions: list[ConditionItem]
    statuses: dict[str, str] = Field(..., description="条件键 → unmet/in_progress/met")
    progress: ConditionProgress


class ConditionStatusUpdateRequest(BaseModel):
    """勾选一条条件的完成状态。"""

    position_id: str = Field(..., min_length=32, max_length=32)
    exam_source: str = Field("national", pattern="^(national|province|kaoyan)$")
    condition_key: str = Field(..., min_length=1, max_length=50)
    status: str = Field(..., pattern="^(unmet|in_progress|met)$")
