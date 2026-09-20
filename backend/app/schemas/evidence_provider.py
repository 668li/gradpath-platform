from pydantic import BaseModel, Field


class ProviderRouteRequest(BaseModel):
    hypothesis: str = Field(..., min_length=1, max_length=2000)


class ProviderRouteItem(BaseModel):
    name: str
    label: str
    description: str
    matched_needs: list[str]


class ProviderRouteResponse(BaseModel):
    hypothesis: str
    providers: list[ProviderRouteItem]


class ProviderSearchRequest(BaseModel):
    hypothesis: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class ProviderEvidenceItem(BaseModel):
    title: str
    claim: str
    source_url: str | None
    reliability: int
    metadata: dict


class ProviderSearchResponse(BaseModel):
    provider: str
    label: str
    count: int
    items: list[ProviderEvidenceItem]
