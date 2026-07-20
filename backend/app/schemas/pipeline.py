# backend/app/schemas/pipeline.py
"""Pipeline Pydantic schemas。"""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator


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
    """数据源响应。

    修复: FASTAPI-RESP-001 — 不再返回 api_key 字段，避免敏感凭证泄漏给客户端。
    保留 has_api_key 布尔值方便前端展示"已配置"状态。
    """
    id: str
    name: str
    source_type: str
    api_url: str | None = None
    has_api_key: bool = False
    data_mapping: dict | None = None
    is_active: bool

    @field_validator("id", mode="before")
    @classmethod
    def convert_uuid(cls, v):
        return str(v) if hasattr(v, "hex") else v

    @field_validator("has_api_key", mode="before")
    @classmethod
    def _derive_has_api_key(cls, v):
        # 直接传布尔值时直接返回；ORM 对象无该字段时此处不会触发，
        # 由 model_validator 兜底从 api_key 推导。
        if isinstance(v, bool):
            return v
        return bool(v)

    @model_validator(mode="before")
    @classmethod
    def _from_orm_with_api_key_flag(cls, data):
        # 兼容 ORM 对象：从 api_key 推导 has_api_key，并删除 api_key 防止返回。
        if hasattr(data, "api_key"):
            api_key = getattr(data, "api_key", None)
            data_dict = {
                "id": getattr(data, "id", None),
                "name": getattr(data, "name", None),
                "source_type": getattr(data, "source_type", None),
                "api_url": getattr(data, "api_url", None),
                "has_api_key": bool(api_key),
                "data_mapping": getattr(data, "data_mapping", None),
                "is_active": getattr(data, "is_active", False),
            }
            return data_dict
        return data

    model_config = {"from_attributes": True}


class PipelineStats(BaseModel):
    total_reports: int
    published_count: int
    pending_count: int
    failed_count: int
