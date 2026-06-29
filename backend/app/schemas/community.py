# backend/app/schemas/community.py
"""社区毕业去向报告的 Pydantic Schema 定义。"""
from pydantic import BaseModel, field_validator

from app.models.community_report import DestinationType, SalaryRange
from app.models.employment_data import Degree


class CommunitySubmit(BaseModel):
    school_name: str
    major: str
    graduation_year: int
    degree: Degree = Degree.bachelor
    destination_type: DestinationType
    employer: str | None = None
    city: str | None = None
    industry: str | None = None
    salary_range: SalaryRange | None = None


class CommunityReportResponse(BaseModel):
    id: str
    school_name: str
    major: str
    graduation_year: int
    degree: str
    destination_type: str
    employer: str | None = None
    city: str | None = None
    industry: str | None = None
    salary_range: str | None = None

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def convert_id(cls, v):
        """将 UUID 转为字符串。"""
        return str(v) if v is not None else v

    @field_validator("degree", "destination_type", "salary_range", mode="before")
    @classmethod
    def convert_enum(cls, v):
        """将枚举成员转为对应的字符串值。"""
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)


class AggregateQuery(BaseModel):
    school: str
    major: str
    year: int | None = None


class AggregateResponse(BaseModel):
    school: str
    major: str
    sample_count: int
    sufficient: bool
    destination_distribution: dict[str, float] | None = None
    top_employers: list[dict] | None = None
    top_cities: list[dict] | None = None
    top_industries: list[dict] | None = None
    salary_distribution: dict[str, int] | None = None


class CommunityStats(BaseModel):
    total_reports: int
    school_count: int
    major_count: int
