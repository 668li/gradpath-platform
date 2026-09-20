from datetime import date, datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.path_comparison import DecisionEngineRequest


HypothesisStatus = Literal["open", "validated", "invalidated", "superseded"]
EvidenceSourceType = Literal["official", "dataset", "peer", "user", "research", "other"]
EvidenceStance = Literal["supports", "refutes", "neutral"]


class HypothesisCreate(BaseModel):
    statement: str = Field(..., min_length=1, max_length=2000)
    importance: int = Field(default=3, ge=1, le=5)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: HypothesisStatus = "open"
    verification_question: str | None = Field(default=None, max_length=2000)
    validation_action: str | None = Field(default=None, max_length=2000)
    metadata: dict = Field(default_factory=dict)


class HypothesisUpdate(BaseModel):
    statement: str | None = Field(default=None, min_length=1, max_length=2000)
    importance: int | None = Field(default=None, ge=1, le=5)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: HypothesisStatus | None = None
    verification_question: str | None = Field(default=None, max_length=2000)
    validation_action: str | None = Field(default=None, max_length=2000)
    metadata: dict | None = None


class HypothesisResponse(BaseModel):
    id: UUID
    user_id: UUID
    decision_id: UUID
    statement: str
    importance: int
    confidence: float
    status: HypothesisStatus
    verification_question: str | None
    validation_action: str | None
    metadata: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceCreate(BaseModel):
    hypothesis_id: UUID | None = None
    title: str = Field(..., min_length=1, max_length=200)
    claim: str = Field(..., min_length=1, max_length=4000)
    source_url: str | None = Field(default=None, max_length=2000)
    source_type: EvidenceSourceType = "other"
    reliability: int = Field(default=3, ge=1, le=5)
    stance: EvidenceStance = "neutral"
    observed_on: date | None = None
    excerpt: str | None = Field(default=None, max_length=2000)
    metadata: dict = Field(default_factory=dict)


class EvidenceUpdate(BaseModel):
    hypothesis_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    claim: str | None = Field(default=None, min_length=1, max_length=4000)
    source_url: str | None = Field(default=None, max_length=2000)
    source_type: EvidenceSourceType | None = None
    reliability: int | None = Field(default=None, ge=1, le=5)
    stance: EvidenceStance | None = None
    observed_on: date | None = None
    excerpt: str | None = Field(default=None, max_length=2000)
    metadata: dict | None = None


class EvidenceResponse(BaseModel):
    id: UUID
    user_id: UUID
    decision_id: UUID
    hypothesis_id: UUID | None
    title: str
    claim: str
    source_url: str | None
    source_type: EvidenceSourceType
    reliability: int
    stance: EvidenceStance
    observed_on: date | None
    excerpt: str | None
    metadata: dict
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EvidenceReadinessResponse(BaseModel):
    decision_id: UUID
    hypotheses_total: int
    hypotheses_with_evidence: int
    hypotheses_unverified: int
    evidence_total: int
    evidence_supporting: int
    evidence_refuting: int
    evidence_neutral: int
    coverage: float = Field(ge=0.0, le=1.0)


class EvidenceImportResponse(BaseModel):
    decision_id: UUID
    imported: int
    skipped_duplicates: int
    provider: str
    notes: list[str] = Field(default_factory=list)


class PathEngineEvidenceImportRequest(DecisionEngineRequest):
    hypothesis_id: UUID | None = Field(
        default=None,
        description="可选：将所有导入证据绑定到该决策的一条假设",
    )
