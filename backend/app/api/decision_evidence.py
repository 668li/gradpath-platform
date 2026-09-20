"""决策证据链 API — Decision → Hypothesis → Evidence。"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.decision_evidence import (
    EvidenceCreate,
    EvidenceReadinessResponse,
    EvidenceResponse,
    EvidenceUpdate,
    HypothesisCreate,
    HypothesisResponse,
    HypothesisUpdate,
)
from app.services import decision_evidence_service

router = APIRouter(prefix="/api/decisions", tags=["决策证据链"])


@router.get("/{decision_id}/hypotheses", response_model=list[HypothesisResponse])
def get_hypotheses(
    decision_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return decision_evidence_service.list_hypotheses(db, user.id, decision_id)


@router.post(
    "/{decision_id}/hypotheses",
    response_model=HypothesisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hypothesis(
    decision_id: UUID,
    body: HypothesisCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return decision_evidence_service.create_hypothesis(db, user.id, decision_id, body)


@router.patch(
    "/{decision_id}/hypotheses/{hypothesis_id}",
    response_model=HypothesisResponse,
)
def patch_hypothesis(
    decision_id: UUID,
    hypothesis_id: UUID,
    body: HypothesisUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return decision_evidence_service.update_hypothesis(
        db, user.id, decision_id, hypothesis_id, body
    )


@router.delete(
    "/{decision_id}/hypotheses/{hypothesis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_hypothesis(
    decision_id: UUID,
    hypothesis_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    decision_evidence_service.delete_hypothesis(
        db, user.id, decision_id, hypothesis_id
    )


@router.get("/{decision_id}/evidence", response_model=list[EvidenceResponse])
def get_evidence(
    decision_id: UUID,
    hypothesis_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return decision_evidence_service.list_evidence(
        db, user.id, decision_id, hypothesis_id
    )


@router.post(
    "/{decision_id}/evidence",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    decision_id: UUID,
    body: EvidenceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return decision_evidence_service.create_evidence(db, user.id, decision_id, body)


@router.patch(
    "/{decision_id}/evidence/{evidence_id}",
    response_model=EvidenceResponse,
)
def patch_evidence(
    decision_id: UUID,
    evidence_id: UUID,
    body: EvidenceUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return decision_evidence_service.update_evidence(
        db, user.id, decision_id, evidence_id, body
    )


@router.delete(
    "/{decision_id}/evidence/{evidence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_evidence(
    decision_id: UUID,
    evidence_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    decision_evidence_service.delete_evidence(
        db, user.id, decision_id, evidence_id
    )


@router.get(
    "/{decision_id}/evidence-readiness",
    response_model=EvidenceReadinessResponse,
)
def evidence_readiness(
    decision_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return decision_evidence_service.get_evidence_readiness(
        db, user.id, decision_id
    )
