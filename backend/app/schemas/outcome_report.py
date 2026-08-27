"""Outcome Report Pydantic Schemas。"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.models.outcome_report import AdmissionPath, OutcomeType


class OutcomeReportCreate(BaseModel):
    outcome_type: OutcomeType = Field(..., description="grad_civil_career/adjustment/failed")
    target_school: str | None = None
    target_major: str | None = None
    actual_school: str | None = None
    actual_major: str | None = None
    score_total: int | None = None
    score_politics: int | None = None
    score_english: int | None = None
    score_major1: int | None = None
    score_major2: int | None = None
    admission_path: AdmissionPath = AdmissionPath.normal
    year: int = Field(..., ge=2000, le=2099)
    confidence_before: float | None = Field(None, ge=0, le=1)
    satisfaction_after: int | None = Field(None, ge=1, le=5)
    what_i_would_do_differently: str | None = None
    advice_for_others: str | None = None
    is_public: str = "private"


class OutcomeReportResponse(BaseModel):
    id: str
    user_id: str
    outcome_type: str
    target_school: str | None = None
    target_major: str | None = None
    actual_school: str | None = None
    actual_major: str | None = None
    score_total: int | None = None
    score_politics: int | None = None
    score_english: int | None = None
    score_major1: int | None = None
    score_major2: int | None = None
    admission_path: str = "normal"
    year: int
    confidence_before: float | None = None
    satisfaction_after: int | None = None
    what_i_would_do_differently: str | None = None
    advice_for_others: str | None = None
    is_public: str = "private"
    created_at: datetime | None = None

    model_config = {"from_attributes": True}

    @field_validator("id", "user_id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v

    @field_validator("outcome_type", "admission_path", mode="before")
    @classmethod
    def convert_enum(cls, v):
        return v.value if hasattr(v, "value") else str(v)


class OutcomeReportListResponse(BaseModel):
    items: list[OutcomeReportResponse]
    total: int


class OutcomeStatsResponse(BaseModel):
    school: str
    major: str
    total_outcomes: int
    acceptance_rate: float | None = None
    avg_score_total: float | None = None
    score_distribution: dict = {}
    path_breakdown: dict = {}
    common_reflections: list[str] = []
