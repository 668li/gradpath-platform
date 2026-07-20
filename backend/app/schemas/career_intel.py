"""求职作战室 Pydantic schemas。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CompanyIntelQueryRequest(BaseModel):
    company_name: str
    position_name: str


class CompanyIntelSaveRequest(BaseModel):
    company_name: str
    position_name: str
    industry: str = ""
    overtime_intensity: str = "unknown"
    layoff_risk: str = "unknown"
    promotion_outlook: str = "unknown"
    education_barrier: str = "unknown"
    salary_honesty: str = "unknown"
    culture_fit: str = "unknown"
    salary_range: str | None = None
    actual_salary: str | None = None
    interview_style: str | None = None
    interview_rounds: int | None = None
    turnover_rate: str | None = None
    growth_path: str | None = None
    insider_notes: str | None = None
    risk_warnings: list[str] = []
    data_sources: list[str] = []
    tags: list[str] = []
    ai_summary: str | None = None
    is_ai_generated: bool = False


class CompanyIntelResponse(BaseModel):
    id: UUID
    company_name: str
    position_name: str
    industry: str
    overtime_intensity: str
    layoff_risk: str
    promotion_outlook: str
    education_barrier: str
    salary_honesty: str
    culture_fit: str
    salary_range: str | None
    actual_salary: str | None
    interview_style: str | None
    interview_rounds: int | None
    turnover_rate: str | None
    growth_path: str | None
    insider_notes: str | None
    risk_warnings: list
    data_sources: list
    tags: list
    ai_summary: str | None
    is_ai_generated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AICompanyIntelResult(BaseModel):
    company_name: str
    position_name: str
    industry: str
    overtime_intensity: str
    layoff_risk: str
    promotion_outlook: str
    education_barrier: str
    salary_honesty: str
    culture_fit: str
    salary_range: str | None = None
    actual_salary: str | None = None
    interview_style: str | None = None
    interview_rounds: int | None = None
    turnover_rate: str | None = None
    growth_path: str | None = None
    insider_notes: str | None = None
    risk_warnings: list[str] = []
    data_sources: list[str] = []
    tags: list[str] = []
    ai_summary: str


class CareerPositioningCreateRequest(BaseModel):
    education_level: str
    school_tier: str = ""
    major: str | None = None
    graduation_year: int | None = None
    gpa: float | None = None
    internships: str | None = None
    skills: list[str] = []
    competitions: list[str] = []
    projects: str | None = None
    certifications: str | None = None
    target_industry: str | None = None
    target_position: str | None = None
    target_city: str | None = None
    salary_expectation: str | None = None
    other_info: str | None = None


class CompanyRecommendation(BaseModel):
    name: str
    position: str
    tier: str
    reason: str
    probability: int


class SkillGap(BaseModel):
    skill: str
    importance: str
    suggestion: str


class CareerPositioningResponse(BaseModel):
    id: UUID
    education_level: str
    school_tier: str
    major: str | None
    graduation_year: int | None
    gpa: float | None
    internships: str | None
    skills: list
    competitions: list
    projects: str | None
    certifications: str | None
    target_industry: str | None
    target_position: str | None
    target_city: str | None
    salary_expectation: str | None
    other_info: str | None
    ai_assessment: str | None
    competitiveness_score: int | None
    reach_companies: list
    target_companies: list
    safety_companies: list
    salary_estimate: str | None
    skill_gaps: list
    risk_warnings: list
    created_at: datetime

    model_config = {"from_attributes": True}


class CareerDarkKnowledgeResponse(BaseModel):
    id: UUID
    stage: str
    category: str
    title: str
    content: str
    importance: str
    common_misconception: str | None
    actionable_advice: str | None
    verification_method: str | None
    tags: list
    sort_order: int

    model_config = {"from_attributes": True}


class DarkKnowledgeStageInfo(BaseModel):
    stage: str
    stage_name: str
    count: int
