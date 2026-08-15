"""省考职位 Pydantic schemas — 对应 gwy_province_position 表一行。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GwyProvincePositionResponse(BaseModel):
    """省考职位响应 — 对应 gwy_province_position 表一行。"""

    id: str
    year: int
    province: str
    dept_name: str | None
    dept_code: str | None
    position_name: str | None
    position_code: str
    position_desc: str | None
    position_type: str | None
    recruit_count: int | None
    education_req: str | None
    degree_req: str | None
    major_req_grad: str | None
    major_req_undergrad: str | None
    major_req_junior: str | None
    grassroots_exp_req: str | None
    psych_test: str | None
    fresh_grad_only: str | None
    other_requirements: str | None
    exam_region: str | None
    sheet_name: str | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GwyProvincePositionListResponse(BaseModel):
    """省考职位列表响应"""

    items: list[GwyProvincePositionResponse]
    total: int
    page: int
    page_size: int


class GwyProvincePositionStatsGroup(BaseModel):
    """统计分组项 — 如按招录系统分组: [{key: "公安", count: 863}, ...]"""

    key: str
    count: int


class GwyProvincePositionStatsResponse(BaseModel):
    """省考职位统计响应 — 总数 + 按招录系统/学历/考区/应届限制分组"""

    total: int
    total_recruit: int
    by_sheet: list[GwyProvincePositionStatsGroup]
    by_education: list[GwyProvincePositionStatsGroup]
    by_region: list[GwyProvincePositionStatsGroup]
    by_fresh_grad_only: list[GwyProvincePositionStatsGroup]
