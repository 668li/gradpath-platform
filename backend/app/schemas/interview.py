# backend/app/schemas/interview.py
"""公司面试经验报告的 Pydantic Schema 定义。"""
from pydantic import BaseModel, field_validator


class InterviewSubmit(BaseModel):
    company: str
    position: str
    interview_year: int
    city: str | None = None
    rounds: int | None = None
    result: str = "pending"
    dimensions: list[str] = []
    difficulty: int | None = None
    summary: str | None = None
    community_report_id: str | None = None


class InterviewReportResponse(BaseModel):
    id: str
    company: str
    position: str
    interview_year: int
    city: str | None = None
    rounds: int | None = None
    result: str
    dimensions: list[str] = []
    difficulty: int | None = None
    summary: str | None = None
    community_report_id: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("id", "community_report_id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        if v is None:
            return v
        return str(v) if hasattr(v, "value") or isinstance(v, object) else v

    @field_validator("result", mode="before")
    @classmethod
    def convert_enum(cls, v):
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)


class InterviewAggregateQuery(BaseModel):
    company: str
    position: str | None = None


class InterviewAggregateResponse(BaseModel):
    company: str
    position: str | None = None
    sample_count: int
    sufficient: bool
    avg_difficulty: float | None = None
    avg_rounds: float | None = None
    result_distribution: dict[str, float] | None = None
    dimension_frequency: dict[str, float] | None = None
    common_positions: list[dict] | None = None


class InterviewStats(BaseModel):
    total_reports: int
    company_count: int
    position_count: int


class CompanyQuery(BaseModel):
    keyword: str = ""
