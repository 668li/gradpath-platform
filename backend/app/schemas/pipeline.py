# backend/app/schemas/pipeline.py
"""Pipeline Pydantic schemas。"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator


class IngestURLRequest(BaseModel):
    source_type: str = "crawl"
    school_slug: str
    year: int
    url: str


class IngestAPIRequest(BaseModel):
    source_type: str = "api"
    school_slug: str
    year: int
    api_source_id: str


class ReportListItem(BaseModel):
    id: str
    school_name: str
    year: int
    source_type: str
    content_type: str | None = None
    parse_status: str
    parse_error: str | None = None
    parsed_at: datetime | None = None
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v

    @field_validator("source_type", "content_type", "parse_status", mode="before")
    @classmethod
    def convert_enum(cls, v):
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    items: list[ReportListItem]
    total: int
    page: int
    page_size: int


class EmploymentDataPreview(BaseModel):
    major: str
    degree: str
    total_graduates: int | None = None
    employment_rate: float | None = None
    further_study_rate: float | None = None

    @field_validator("degree", mode="before")
    @classmethod
    def convert_enum(cls, v):
        if v is None:
            return v
        return v.value if hasattr(v, "value") else str(v)

    model_config = {"from_attributes": True}


class ReportDetail(ReportListItem):
    source_url: str
    employment_data: list[EmploymentDataPreview] = []


class DataSourceCreate(BaseModel):
    name: str
    source_type: str = "api"
    api_url: str | None = None
    api_key: str | None = None
    data_mapping: dict | None = None
    is_active: bool = True


class DataSourceUpdate(BaseModel):
    name: str | None = None
    source_type: str | None = None
    api_url: str | None = None
    api_key: str | None = None
    data_mapping: dict | None = None
    is_active: bool | None = None


class DataSourceResponse(BaseModel):
    id: str
    name: str
    source_type: str
    api_url: str | None = None
    api_key: str | None = None
    data_mapping: dict | None = None
    is_active: bool

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v

    model_config = {"from_attributes": True}


class PipelineStats(BaseModel):
    total_reports: int
    published_count: int
    pending_count: int
    failed_count: int
