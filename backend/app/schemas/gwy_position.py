"""国考职位 Pydantic schemas"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GwyPositionResponse(BaseModel):
    """国考职位响应 — 对应 gwy_position 表一行。"""

    id: str
    year: int
    exam_type: str
    dept_code: str | None
    dept_name: str | None
    bureau: str | None
    agency_type: str | None
    position_name: str | None
    position_attr: str | None
    position_distribution: str | None
    position_desc: str | None
    position_code: str
    org_level: str | None
    exam_category: str | None
    recruit_count: int | None
    major_req: str | None
    education_req: str | None
    degree_req: str | None
    political_status: str | None
    min_work_years: str | None
    grassroots_exp_req: str | None
    professional_test: str | None
    interview_ratio: str | None
    work_location: str | None
    settle_location: str | None
    remarks: str | None
    dept_website: str | None
    phone1: str | None
    phone2: str | None
    phone3: str | None
    sheet_name: str | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GwyPositionListResponse(BaseModel):
    """国考职位列表响应"""

    items: list[GwyPositionResponse]
    total: int
    page: int
    page_size: int


class GwyPositionStatsGroup(BaseModel):
    """统计分组项 — 如按省份统计: [{key: "北京", count: 123}, ...]"""

    key: str
    count: int


class GwyPositionStatsResponse(BaseModel):
    """国考职位统计响应 — 总数 + 按省份/学历/机构层级/考试类别分组"""

    total: int
    by_province: list[GwyPositionStatsGroup]
    by_education: list[GwyPositionStatsGroup]
    by_org_level: list[GwyPositionStatsGroup]
    by_exam_category: list[GwyPositionStatsGroup]
