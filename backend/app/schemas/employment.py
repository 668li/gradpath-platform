# backend/app/schemas/employment.py
from pydantic import BaseModel


class SchoolResponse(BaseModel):
    id: str
    name: str
    slug: str
    code: str | None = None
    report_count: int = 0
    major_count: int = 0


class EmploymentRecordResponse(BaseModel):
    year: int
    degree: str
    total_graduates: int | None
    rates: dict
    employer_ranking: list
    industry_distribution: dict
    destination_region: dict
    school_for_further_study: list


class TrendResponse(BaseModel):
    years: list[int]
    employment_rate: list[float | None]
    further_study_rate: list[float | None]
    civil_service_rate: list[float | None]
    abroad_rate: list[float | None]


class EmploymentSearchResponse(BaseModel):
    school: SchoolResponse | None
    major: str | None
    records: list[EmploymentRecordResponse]
    trend: TrendResponse | None


class EmploymentStatsResponse(BaseModel):
    school_count: int
    report_count: int
    major_count: int
    year_range: tuple[int | None, int | None]
