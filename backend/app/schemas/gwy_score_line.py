"""国考进面分数线 Pydantic schemas"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GwyScoreLineResponse(BaseModel):
    """国考进面分数线响应 — 对应 gwy_score_line 表一行（职位级聚合，无个人信息）。"""

    id: str
    year: int
    batch: str
    dept_name: str | None
    dept_code: str | None
    bureau: str | None
    position_name: str | None
    position_code: str
    min_score: float | None
    source_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GwyScoreLineListResponse(BaseModel):
    """国考进面分数线列表响应"""

    items: list[GwyScoreLineResponse]
    total: int
    page: int
    page_size: int


class GwyScoreLineStatsGroup(BaseModel):
    """统计分组项 — 如按批次: [{key: "首批", count: 7300}, ...]"""

    key: str
    count: int


class GwyScoreLineStatsResponse(BaseModel):
    """国考进面分数线统计响应 — 总数 + 按批次/年份分组 + 平均进面分"""

    total: int
    avg_score: float | None
    by_batch: list[GwyScoreLineStatsGroup]
    by_year: list[GwyScoreLineStatsGroup]
