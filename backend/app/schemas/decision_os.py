"""Decision OS schemas — 决策验证闭环（D9，拍板 09-25）。

draft/confirm 流程：自然语言 → AI 结构化草稿（LLM 不可用时诚实降级）→ 用户确认落库。
证据的 verification_status 不接受客户端指定：创建一律 internal_unverified，
状态只能走 /verify 显式验证（externally_verified 必须带 verification_source，
服务层强制）。术语见仓库 CONTEXT.md。
"""

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.models.decision_os import (
    ActionResultStance,
    DecisionOutcomeKind,
    EvidenceReliability,
    EvidenceSourceType,
    EvidenceStance,
    EvidenceVerificationStatus,
    HypothesisImportance,
    HypothesisStatus,
    ReflectionMatchStatus,
    ValidationActionStatus,
)
from app.models.destination_decision import DestinationType
from app.schemas.decision import DecisionResponse


class StructureRequest(BaseModel):
    raw_text: str = Field(min_length=5, max_length=4000, description="用户自然语言描述的决策")


class DraftHypothesis(BaseModel):
    statement: str = Field(min_length=1, max_length=2000)
    importance: HypothesisImportance = HypothesisImportance.high
    impact: str | None = None


class StructuredDraft(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    context: str | None = None
    options: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    desired_outcome: str | None = None
    hypotheses: list[DraftHypothesis] = Field(default_factory=list)
    evidence_needs: list[str] = Field(default_factory=list)
    ai_used: bool = False


class ConfirmDraftRequest(BaseModel):
    draft: StructuredDraft
    destination_type: DestinationType
    decision_date: date | None = None
    confidence: int = Field(default=3, ge=1, le=5)


class HypothesisCreate(BaseModel):
    statement: str = Field(min_length=1, max_length=2000)
    importance: HypothesisImportance = HypothesisImportance.high
    confidence: int = Field(default=3, ge=1, le=5)
    impact: str | None = None


class HypothesisUpdate(BaseModel):
    statement: str | None = Field(default=None, min_length=1, max_length=2000)
    importance: HypothesisImportance | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)
    status: HypothesisStatus | None = None
    impact: str | None = None
    result: str | None = None


class EvidenceCreate(BaseModel):
    claim: str = Field(min_length=1, max_length=4000)
    decision_id: UUID | None = None
    hypothesis_id: UUID | None = None
    source: str | None = Field(default=None, max_length=500)
    source_url: str | None = None
    source_type: EvidenceSourceType = EvidenceSourceType.user_observed
    reliability: EvidenceReliability = EvidenceReliability.medium
    stance: EvidenceStance = EvidenceStance.neutral
    observed_on: date | None = None
    provider: str | None = Field(default=None, max_length=100)
    notes: str | None = None
    # 注意：没有 verification_status 字段 —— 创建一律 internal_unverified


class EvidenceUpdate(BaseModel):
    claim: str | None = Field(default=None, min_length=1, max_length=4000)
    source: str | None = Field(default=None, max_length=500)
    source_url: str | None = None
    source_type: EvidenceSourceType | None = None
    reliability: EvidenceReliability | None = None
    stance: EvidenceStance | None = None
    observed_on: date | None = None
    notes: str | None = None
    # 同样没有 verification_status：状态只能走 /verify


class EvidenceVerifyRequest(BaseModel):
    verification_status: EvidenceVerificationStatus
    verification_source: str = Field(default="", max_length=2000)
    verified_on: date | None = None


class ValidationActionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    hypothesis_id: UUID | None = None
    uncertainty: str | None = None
    expected_information_gain: str | None = None
    due_date: date | None = None


class ValidationActionUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    status: ValidationActionStatus | None = None
    uncertainty: str | None = None
    expected_information_gain: str | None = None
    due_date: date | None = None


class ActionCompleteRequest(BaseModel):
    result: str = Field(min_length=1, max_length=4000)
    result_stance: ActionResultStance
    # 仅当显式携带时才改假设状态 —— 系统不替用户下"假设成立/证伪"的结论
    hypothesis_status_update: HypothesisStatus | None = None


class OutcomeCreate(BaseModel):
    kind: DecisionOutcomeKind = DecisionOutcomeKind.direct
    summary: str = Field(min_length=1, max_length=4000)
    observed_on: date | None = None
    notes: str | None = None


class ReflectionCreate(BaseModel):
    prediction_error: str | None = None
    wrong_assumption: str | None = None
    omitted_factor: str | None = None
    lesson: str | None = None
    match_status: ReflectionMatchStatus = ReflectionMatchStatus.unknown
    new_principle: str | None = None

    @model_validator(mode="after")
    def _require_content(self) -> "ReflectionCreate":
        fields = (
            self.prediction_error,
            self.wrong_assumption,
            self.omitted_factor,
            self.lesson,
            self.new_principle,
        )
        if not any(f and f.strip() for f in fields):
            raise ValueError("复盘至少要填写预测误差/错误假设/遗漏因素/教训/新原则之一")
        return self


class HypothesisResponse(BaseModel):
    id: UUID
    decision_id: UUID
    statement: str
    importance: HypothesisImportance
    confidence: int
    status: HypothesisStatus
    impact: str | None = None
    result: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvidenceResponse(BaseModel):
    id: UUID
    decision_id: UUID | None = None
    hypothesis_id: UUID | None = None
    claim: str
    source: str | None = None
    source_url: str | None = None
    source_type: EvidenceSourceType
    reliability: EvidenceReliability
    stance: EvidenceStance
    observed_on: date | None = None
    provider: str | None = None
    verification_status: EvidenceVerificationStatus
    verification_source: str | None = None
    verified_on: date | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ValidationActionResponse(BaseModel):
    id: UUID
    decision_id: UUID
    hypothesis_id: UUID | None = None
    title: str
    uncertainty: str | None = None
    expected_information_gain: str | None = None
    status: ValidationActionStatus
    result: str | None = None
    result_stance: ActionResultStance | None = None
    due_date: date | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OutcomeResponse(BaseModel):
    id: UUID
    decision_id: UUID
    kind: DecisionOutcomeKind
    summary: str
    observed_on: date | None = None
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReflectionResponse(BaseModel):
    id: UUID
    decision_id: UUID
    prediction_error: str | None = None
    wrong_assumption: str | None = None
    omitted_factor: str | None = None
    lesson: str | None = None
    match_status: ReflectionMatchStatus
    new_principle: str | None = None
    ai_summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HypothesisCard(HypothesisResponse):
    """假设卡片 = 假设本体 + 证据立场计数（诚实计数，不做伪精确覆盖率）。"""

    evidence_count: int = 0
    supporting: int = 0
    contradicting: int = 0
    neutral: int = 0


class DecisionCard(BaseModel):
    decision: DecisionResponse
    hypotheses: list[HypothesisCard] = Field(default_factory=list)
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    actions: list[ValidationActionResponse] = Field(default_factory=list)
    outcomes: list[OutcomeResponse] = Field(default_factory=list)
    reflections: list[ReflectionResponse] = Field(default_factory=list)
