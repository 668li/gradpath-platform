"""考公作战室 Pydantic schemas。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PostIntelQueryRequest(BaseModel):
    region: str
    department: str
    post_name: str
    exam_type: str = ""


class PostIntelSaveRequest(BaseModel):
    region: str
    department: str
    post_name: str
    exam_type: str = ""
    real_competition: str = "unknown"
    treatment_level: str = "unknown"
    promotion_speed: str = "unknown"
    workload: str = "unknown"
    radish_post: str = "unknown"
    service_period: str = "unknown"
    admission_ratio: str | None = None
    cutoff_score: int | None = None
    salary_estimate: str | None = None
    housing_fund: str | None = None
    bonus_info: str | None = None
    department_tier: str | None = None
    work_content: str | None = None
    insider_notes: str | None = None
    risk_warnings: list[str] = []
    data_sources: list[str] = []
    tags: list[str] = []
    ai_summary: str | None = None
    is_ai_generated: bool = False


class PostIntelResponse(BaseModel):
    id: UUID
    region: str
    department: str
    post_name: str
    exam_type: str
    real_competition: str
    treatment_level: str
    promotion_speed: str
    workload: str
    radish_post: str
    service_period: str
    admission_ratio: str | None
    cutoff_score: int | None
    salary_estimate: str | None
    housing_fund: str | None
    bonus_info: str | None
    department_tier: str | None
    work_content: str | None
    insider_notes: str | None
    risk_warnings: list
    data_sources: list
    tags: list
    ai_summary: str | None
    is_ai_generated: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AIPostIntelResult(BaseModel):
    region: str
    department: str
    post_name: str
    exam_type: str
    real_competition: str
    treatment_level: str
    promotion_speed: str
    workload: str
    radish_post: str
    service_period: str
    admission_ratio: str | None = None
    cutoff_score: int | None = None
    salary_estimate: str | None = None
    housing_fund: str | None = None
    bonus_info: str | None = None
    department_tier: str | None = None
    work_content: str | None = None
    insider_notes: str | None = None
    risk_warnings: list[str] = []
    data_sources: list[str] = []
    tags: list[str] = []
    ai_summary: str


class CivilServicePositioningCreateRequest(BaseModel):
    education_level: str
    school_tier: str = ""
    major: str | None = None
    is_party_member: bool = False
    student_leader: bool = False
    has_honors: bool = False
    is_fresh_graduate: bool = True
    target_region: str | None = None
    target_type: str | None = None
    family_background: str | None = None
    other_info: str | None = None


class PostRecommendation(BaseModel):
    region: str
    department: str
    post: str
    reason: str
    probability: int


class CivilServicePositioningResponse(BaseModel):
    id: UUID
    education_level: str
    school_tier: str
    major: str | None
    is_party_member: bool
    student_leader: bool
    has_honors: bool
    is_fresh_graduate: bool
    target_region: str | None
    target_type: str | None
    family_background: str | None
    other_info: str | None
    ai_assessment: str | None
    competitiveness_score: int | None
    eligible_for_xuandiao: bool
    reach_posts: list
    target_posts: list
    safety_posts: list
    preparation_timeline: str | None
    risk_warnings: list
    created_at: datetime

    model_config = {"from_attributes": True}


class CivilServiceDarkKnowledgeResponse(BaseModel):
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
