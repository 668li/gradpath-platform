"""Decision OS API — 决策验证闭环（D9 拍板 09-25）。

所有端点均要求登录；所有权由服务层 user_id 过滤强制（查不到=404，
不泄露他用户资源存在性）。证据闸：创建一律 internal_unverified，
状态只经 /verify 推进。本路由经 app/api/__init__.py 自动注册。
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.decision_os import (
    ActionCompleteRequest,
    ConfirmDraftRequest,
    DecisionCard,
    EvidenceCandidate,
    EvidenceCreate,
    EvidenceResponse,
    EvidenceUpdate,
    EvidenceVerifyRequest,
    HypothesisCreate,
    HypothesisResponse,
    HypothesisUpdate,
    OutcomeCreate,
    OutcomeResponse,
    ProviderSearchRequest,
    ReflectionCreate,
    ReflectionResponse,
    StructuredDraft,
    StructureRequest,
    ValidationActionCreate,
    ValidationActionResponse,
    ValidationActionUpdate,
)
from app.services import decision_os_service as service
from app.services import evidence_provider_service as provider_service

router = APIRouter(prefix="/api/decision-os", tags=["决策OS"])


# ---------------------------------------------------------------- AI 结构化
@router.post("/structure", response_model=StructuredDraft)
async def structure(
    data: StructureRequest,
    user: User = Depends(get_current_user),
):
    """自然语言 → 决策卡草稿。LLM 不可用时诚实降级（ai_used=False），不编造假设。"""
    return await service.structure_draft(data.raw_text)


@router.post(
    "/decisions/confirm-draft",
    response_model=DecisionCard,
    status_code=status.HTTP_201_CREATED,
)
def confirm_draft(
    data: ConfirmDraftRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """用户确认草稿 → 创建决策与关键假设。最终决策权在用户。"""
    decision = service.confirm_draft(db, user.id, data)
    return service.get_card(db, user.id, decision.id)


@router.get("/decisions/{decision_id}/card", response_model=DecisionCard)
def get_card(
    decision_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.get_card(db, user.id, decision_id)


# ---------------------------------------------------------------- hypotheses
@router.post(
    "/decisions/{decision_id}/hypotheses",
    response_model=HypothesisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hypothesis(
    decision_id: UUID,
    data: HypothesisCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_hypothesis(db, user.id, decision_id, data)


@router.patch("/hypotheses/{hypothesis_id}", response_model=HypothesisResponse)
def update_hypothesis(
    hypothesis_id: UUID,
    data: HypothesisUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.update_hypothesis(db, user.id, hypothesis_id, data)


@router.delete("/hypotheses/{hypothesis_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hypothesis(
    hypothesis_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service.delete_hypothesis(db, user.id, hypothesis_id)


# ---------------------------------------------------------------- evidence
@router.post(
    "/decisions/{decision_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_decision_evidence(
    decision_id: UUID,
    data: EvidenceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_evidence(db, user.id, data, decision_id=decision_id)


@router.post(
    "/hypotheses/{hypothesis_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hypothesis_evidence(
    hypothesis_id: UUID,
    data: EvidenceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_evidence(db, user.id, data, hypothesis_id=hypothesis_id)


@router.patch("/evidence/{evidence_id}", response_model=EvidenceResponse)
def update_evidence(
    evidence_id: UUID,
    data: EvidenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.update_evidence(db, user.id, evidence_id, data)


@router.post("/evidence/{evidence_id}/verify", response_model=EvidenceResponse)
def verify_evidence(
    evidence_id: UUID,
    data: EvidenceVerifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """显式验证。externally_verified 必须带 verification_source（证据闸）。"""
    return service.verify_evidence(db, user.id, evidence_id, data)


@router.delete("/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service.delete_evidence(db, user.id, evidence_id)


# ---------------------------------------------------------------- validation actions
@router.post(
    "/decisions/{decision_id}/actions",
    response_model=ValidationActionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_action(
    decision_id: UUID,
    data: ValidationActionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_action(db, user.id, decision_id, data)


@router.patch("/actions/{action_id}", response_model=ValidationActionResponse)
def update_action(
    action_id: UUID,
    data: ValidationActionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.update_action(db, user.id, action_id, data)


@router.post("/actions/{action_id}/complete", response_model=ValidationActionResponse)
def complete_action(
    action_id: UUID,
    data: ActionCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """完成行动并记录结果。只有显式携带 hypothesis_status_update 才改假设状态。"""
    return service.complete_action(db, user.id, action_id, data)


@router.delete("/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action(
    action_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service.delete_action(db, user.id, action_id)


# ---------------------------------------------------------------- provider router
@router.get("/hypotheses/{hypothesis_id}/providers")
def list_providers(
    hypothesis_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """白名单 Provider 清单（先过所有权，他人假设看不到面板）。"""
    service.get_hypothesis(db, user.id, hypothesis_id)
    return provider_service.list_providers()


@router.post(
    "/hypotheses/{hypothesis_id}/providers/{provider_name}/search",
    response_model=list[EvidenceCandidate],
)
def search_provider(
    hypothesis_id: UUID,
    provider_name: str,
    data: ProviderSearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """白名单内部库检索候选证据。未知 provider=404，绝不随机路由。"""
    return provider_service.search_provider(db, user.id, hypothesis_id, provider_name, data.query)


# ---------------------------------------------------------------- outcomes / reflections
@router.post(
    "/decisions/{decision_id}/outcomes",
    response_model=OutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_outcome(
    decision_id: UUID,
    data: OutcomeCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_outcome(db, user.id, decision_id, data)


@router.post(
    "/decisions/{decision_id}/reflections",
    response_model=ReflectionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reflection(
    decision_id: UUID,
    data: ReflectionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return service.create_reflection(db, user.id, decision_id, data)
