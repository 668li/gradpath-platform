# backend/app/schemas/ai.py
"""AI 决策指导与外部数据查询的 Pydantic Schema 定义。"""
from datetime import date

from pydantic import BaseModel, Field, field_validator, model_validator


# ======================================================================
# AI 决策指导
# ======================================================================

class DecisionAdviceRequest(BaseModel):
    """AI 决策指导请求体。"""

    destination_type: str = Field(..., description="去向类型（employment/postgrad/...）")
    company: str | None = Field(None, max_length=100, description="意向公司")
    position: str | None = Field(None, max_length=100, description="意向岗位")
    city: str | None = Field(None, max_length=100, description="意向城市")
    expected_salary: str | None = Field(None, max_length=50, description="期望薪资区间（如 25k_50k）")


class AlternativeOption(BaseModel):
    """备选方案条目。"""

    option: str
    reason: str


class DecisionAdviceResponse(BaseModel):
    """AI 决策指导响应体（对应 LLM 输出的 JSON 结构）。"""

    summary: str
    pros: list[str]
    cons: list[str]
    market_analysis: str
    alternatives: list[AlternativeOption]
    skill_gap: list[str]
    confidence: int
    advice: str


# ======================================================================
# AI 成长洞察
# ======================================================================

class GrowthInsightRequest(BaseModel):
    """成长洞察请求体。"""

    period_start: date = Field(..., description="分析时段开始日期")
    period_end: date = Field(..., description="分析时段结束日期")

    @model_validator(mode="after")
    def _check_period_order(self):
        """period_end 不得早于 period_start。"""
        if self.period_end < self.period_start:
            raise ValueError("period_end 不能早于 period_start")
        return self


class GrowthInsightResponse(BaseModel):
    """成长洞察响应体（对应 LLM 输出的 JSON 结构）。"""

    growth_score: int
    trend: str
    strengths: list[str]
    gaps: list[str]
    recommendations: list[str]
    summary: str


# ======================================================================
# 外部数据查询响应
# ======================================================================

class CompanyResponse(BaseModel):
    """公司元数据响应。"""

    id: str
    name: str
    industry: str
    size: str
    stage: str | None = None
    headquarters: str | None = None
    description: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_id(cls, v):
        """将 UUID 转为字符串。"""
        return str(v) if v is not None else v

    @field_validator("size", mode="before")
    @classmethod
    def convert_enum(cls, v):
        """将枚举成员转为对应的字符串值。"""
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)


class SalaryBenchmarkResponse(BaseModel):
    """薪资基准响应。"""

    id: str
    company: str
    position: str
    city: str | None = None
    experience_level: str
    salary_min: int
    salary_median: int
    salary_max: int
    source: str
    year: int

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_id(cls, v):
        """将 UUID 转为字符串。"""
        return str(v) if v is not None else v

    @field_validator("experience_level", mode="before")
    @classmethod
    def convert_enum(cls, v):
        """将枚举成员转为对应的字符串值。"""
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)


class MarketDataResponse(BaseModel):
    """市场宏观数据响应。"""

    id: str
    indicator: str
    category: str
    value: float
    unit: str
    region: str | None = None
    industry: str | None = None
    year: int
    source: str

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_id(cls, v):
        """将 UUID 转为字符串。"""
        return str(v) if v is not None else v
