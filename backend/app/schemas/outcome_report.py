"""Outcome Report Pydantic Schemas。"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.outcome_report import AdmissionPath, OutcomeType


class OutcomeReportCreate(BaseModel):
    outcome_type: OutcomeType = Field(..., description="grad_civil_career/adjustment/failed")
    target_school: Optional[str] = None
    target_major: Optional[str] = None
    actual_school: Optional[str] = None
    actual_major: Optional[str] = None
    score_total: Optional[int] = None
    score_politics: Optional[int] = None
    score_english: Optional[int] = None
    score_major1: Optional[int] = None
    score_major2: Optional[int] = None
    admission_path: AdmissionPath = AdmissionPath.normal
    year: int = Field(..., ge=2000, le=2099)
    confidence_before: Optional[float] = Field(None, ge=0, le=1)
    satisfaction_after: Optional[int] = Field(None, ge=1, le=5)
    what_i_would_do_differently: Optional[str] = None
    advice_for_others: Optional[str] = None
    is_public: str = "private"


class OutcomeReportResponse(BaseModel):
    id: str
    user_id: str
    outcome_type: str
    target_school: Optional[str] = None
    target_major: Optional[str] = None
    actual_school: Optional[str] = None
    actual_major: Optional[str] = None
    score_total: Optional[int] = None
    score_politics: Optional[int] = None
    score_english: Optional[int] = None
    score_major1: Optional[int] = None
    score_major2: Optional[int] = None
    admission_path: str = "normal"
    year: int
    confidence_before: Optional[float] = None
    satisfaction_after: Optional[int] = None
    what_i_would_do_differently: Optional[str] = None
    advice_for_others: Optional[str] = None
    is_public: str = "private"
    created_at: Optional[datetime] = None

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
    acceptance_rate: Optional[float] = None
    avg_score_total: Optional[float] = None
    score_distribution: dict = {}
    path_breakdown: dict = {}
    common_reflections: list[str] = []
