"""Evidence Provider API：让 Hypothesis 可解释地选择现有数据源。"""
from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.decision_hypothesis import DecisionHypothesis
from app.models.user import User
from app.schemas.evidence_provider import (
    ProviderRouteItem, ProviderRouteRequest, ProviderRouteResponse,
    ProviderSearchRequest, ProviderSearchResponse,
)
from app.services.evidence_provider_service import PROVIDERS, route_hypothesis, route_hypothesis_with_ai, search_provider

router = APIRouter(prefix="/api/evidence-providers", tags=["Evidence Providers"])


@router.get("")
def list_providers():
    return [{"name": p.name, "label": p.label, "description": p.description, "needs": list(p.needs)} for p in PROVIDERS]


@router.post("/route", response_model=ProviderRouteResponse)
def route_providers(body: ProviderRouteRequest):
    providers = route_hypothesis(body.hypothesis)
    return ProviderRouteResponse(
        hypothesis=body.hypothesis,
        providers=[
            ProviderRouteItem(
                name=p.name,
                label=p.label,
                description=p.description,
                matched_needs=[k for k in p.needs if k.lower() in body.hypothesis.lower()],
            )
            for p in providers
        ],
    )


@router.post("/{provider_name}/search", response_model=ProviderSearchResponse)
def search(provider_name: str, body: ProviderSearchRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        result = search_provider(db, provider_name, body.hypothesis, body.limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return result


@router.post("/decisions/{decision_id}/hypotheses/{hypothesis_id}/discover")
def discover_for_hypothesis(
    decision_id: UUID,
    hypothesis_id: UUID,
    body: ProviderSearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """自动将 Hypothesis 路由到现有 Provider，并返回候选证据。
    
    只做 discovery，不直接写入 DecisionEvidence，避免未经审计的内部数据被误认为外部已验证事实。
    """
    hypothesis = (
        db.query(DecisionHypothesis)
        .filter(
            DecisionHypothesis.id == hypothesis_id,
            DecisionHypothesis.decision_id == decision_id,
            DecisionHypothesis.user_id == user.id,
        )
        .first()
    )
    if not hypothesis:
        raise HTTPException(status_code=404, detail="决策假设不存在或无权访问")

    providers = route_hypothesis(hypothesis.statement)
    discoveries = [
        search_provider(db, provider.name, hypothesis.statement, body.limit)
        for provider in providers
    ]
    return {
        "decision_id": str(decision_id),
        "hypothesis_id": str(hypothesis_id),
        "hypothesis": hypothesis.statement,
        "providers": discoveries,
        "verification_policy": "internal_unverified_until_external_check",
    }
