"""考研情报 Schema — 院校情报、自我定位、暗知识。"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ===== 院校情报 =====
class IntelQueryRequest(BaseModel):
    """AI 院校情报查询请求。"""
    school_name: str = Field(..., description="院校名称")
    major_name: str = Field(..., description="专业名称")


class IntelSaveRequest(BaseModel):
    """保存院校情报。"""
    school_name: str
    major_name: str
    school_tier: str = ""
    year: int = 2026
    background_discrimination: str = "unknown"
    first_choice_protection: str = "unknown"
    admission_ratio: str | None = None
    push_ratio: str | None = None
    actual_quota: int | None = None
    score_line: int | None = None
    retest_weight: str | None = None
    retest_format: str | None = None
    score_suppression: str = "unknown"
    transfer_friendly: str = "unknown"
    insider_notes: str | None = None
    data_sources: list = []
    tags: list = []
    ai_summary: str | None = None
    is_ai_generated: bool = False


class IntelResponse(BaseModel):
    """院校情报响应。"""
    id: UUID
    school_name: str
    major_name: str
    school_tier: str
    year: int
    background_discrimination: str
    first_choice_protection: str
    admission_ratio: str | None = None
    push_ratio: str | None = None
    actual_quota: int | None = None
    score_line: int | None = None
    retest_weight: str | None = None
    retest_format: str | None = None
    score_suppression: str = "unknown"
    transfer_friendly: str = "unknown"
    insider_notes: str | None = None
    data_sources: list = []
    tags: list = []
    ai_summary: str | None = None
    is_ai_generated: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class AIIntelResult(BaseModel):
    """AI 生成的院校情报结果。"""
    school_name: str
    major_name: str
    school_tier: str = ""
    background_discrimination: str = "unknown"
    first_choice_protection: str = "unknown"
    admission_ratio: str | None = None
    push_ratio: str | None = None
    actual_quota: int | None = None
    score_line: int | None = None
    retest_weight: str | None = None
    retest_format: str | None = None
    score_suppression: str = "unknown"
    transfer_friendly: str = "unknown"
    insider_notes: str | None = None
    data_sources: list = []
    tags: list = []
    ai_summary: str = ""


# ===== 自我定位 =====
class PositioningCreateRequest(BaseModel):
    """创建自我定位。"""
    undergrad_tier: str = Field(..., description="本科层次: 985/211/一本/二本/三本/专升本")
    undergrad_major: str | None = None
    gpa: float | None = None
    gpa_rank: str | None = None
    english_level: str | None = None
    english_score: int | None = None
    research_experience: str | None = None
    competitions: list = []
    awards: str | None = None
    internships: str | None = None
    target_school: str | None = None
    target_major: str | None = None
    target_region: str | None = None
    other_info: str | None = None


class SchoolRecommendation(BaseModel):
    """单个院校推荐。"""
    name: str
    major: str = ""
    tier: str = ""
    reason: str = ""
    probability: int = 0


class PositioningResponse(BaseModel):
    """自我定位响应。"""
    id: UUID
    undergrad_tier: str
    undergrad_major: str | None = None
    gpa: float | None = None
    gpa_rank: str | None = None
    english_level: str | None = None
    english_score: int | None = None
    research_experience: str | None = None
    competitions: list = []
    awards: str | None = None
    internships: str | None = None
    target_school: str | None = None
    target_major: str | None = None
    target_region: str | None = None
    other_info: str | None = None
    ai_assessment: str | None = None
    reach_schools: list = []
    target_schools: list = []
    safety_schools: list = []
    success_probability: int | None = None
    risk_warnings: list = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ===== 暗知识 =====
class DarkKnowledgeResponse(BaseModel):
    """暗知识响应。"""
    id: UUID
    stage: str
    category: str
    title: str
    content: str
    importance: str
    common_misconception: str | None = None
    actionable_advice: str | None = None
    verification_method: str | None = None
    tags: list = []
    sort_order: int = 0

    model_config = {"from_attributes": True}


# ===== 研招网真实专业目录 =====
class GradYanzhaoProgramResponse(BaseModel):
    """研招网专业目录响应。"""
    id: UUID
    university_name: str
    department: str
    major_name: str
    degree_type: str
    research_directions: list = []
    enrollment_quota: int | None = None
    tuition: str | None = None
    duration: str | None = None
    study_mode: str | None = None
    admission_requirements: str | None = None
    contact_info: str | None = None
    source_url: str | None = None
    year: int = 2026
    data_sources: list = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ===== 真实复试分数线 =====
class GradScorelineRecordResponse(BaseModel):
    """院校复试分数线响应。"""
    id: UUID
    university_name: str
    major_name: str
    degree_type: str | None = None
    year: int
    total_score_line: int | None = None
    politics_score: int | None = None
    foreign_language_score: int | None = None
    business_1_score: int | None = None
    business_2_score: int | None = None
    enrollment_count: int | None = None
    application_count: int | None = None
    adjustment_count: int | None = None
    data_sources: list = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GradScorelineTrendResponse(BaseModel):
    """复试分数线趋势响应（按院校+专业聚合多年数据）。"""
    university_name: str
    major_name: str
    degree_type: str | None = None
    years: list[int]
    total_score_lines: list[int | None]
    politics_scores: list[int | None]
    foreign_language_scores: list[int | None]
    business_1_scores: list[int | None]
    business_2_scores: list[int | None]
    application_counts: list[int | None]
    enrollment_counts: list[int | None]


# ===== 调剂信息 =====
class GradAdjustmentInfoResponse(BaseModel):
    """调剂信息响应。"""
    id: UUID
    university_name: str
    department: str
    major_name: str
    degree_type: str | None = None
    original_major_range: str | None = None
    adjustment_quota: int | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    deadline: str | None = None
    source_url: str | None = None
    year: int = 2025
    status: str = "open"
    data_sources: list = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GradSchoolDataSummaryResponse(BaseModel):
    """院校数据汇总（用于前端卡片展示）。"""
    university_name: str
    program_count: int
    latest_year: int | None = None
    latest_scoreline: int | None = None
    scoreline_trend: str = "stable"  # up / down / stable
    has_adjustment: bool = False
    adjustment_count: int = 0


# ===== 分页响应 =====
class PaginatedResponse(BaseModel):
    """分页响应基础模型。"""
    items: list = []
    total: int = 0
    page: int = 1
    limit: int = 20
    pages: int = 0


class PaginatedDarkKnowledgeResponse(PaginatedResponse):
    """暗知识分页响应。"""
    items: list[DarkKnowledgeResponse] = []


class PaginatedYanzhaoProgramResponse(PaginatedResponse):
    """研招网专业目录分页响应。"""
    items: list[GradYanzhaoProgramResponse] = []


class PaginatedScorelineResponse(PaginatedResponse):
    """分数线记录分页响应。"""
    items: list[GradScorelineRecordResponse] = []
