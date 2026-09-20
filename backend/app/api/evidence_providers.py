"""Evidence Provider API：让 Hypothesis 可解释地选择现有数据源。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.evidence_provider import (
    ProviderRouteItem, ProviderRouteRequest, ProviderRouteResponse,
    ProviderSearchRequest, ProviderSearchResponse,
)
from app.services.evidence_provider_service import PROVIDERS, route_hypothesis, search_provider

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
