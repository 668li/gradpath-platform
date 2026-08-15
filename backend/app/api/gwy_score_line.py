"""国考进面分数线 API — 公开只读：列表（筛选+分页）、统计。

数据来源：2026 国考面试人员名单（fetch_gwy_interview.py 采集，职位级聚合，
已剔除准考证号/姓名等个人信息），仅做查询展示。
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.gwy_score_line import GwyScoreLine
from app.schemas.gwy_score_line import (
    GwyScoreLineListResponse,
    GwyScoreLineResponse,
    GwyScoreLineStatsGroup,
    GwyScoreLineStatsResponse,
)
from app.services.employment_service import escape_like

router = APIRouter(prefix="/api/gwy-score-lines", tags=["国考进面分数线"])


@router.get("/stats", response_model=GwyScoreLineStatsResponse)
def gwy_score_line_stats(
    year: Optional[int] = Query(None, description="招考年份（默认全部）"),
    db: Session = Depends(get_db),
):
    """进面分数线统计：总数 + 平均进面分 + 按批次/年份分组计数。"""
    base = db.query(GwyScoreLine)
    if year:
        base = base.filter(GwyScoreLine.year == year)
    total = base.count()

    avg = base.with_entities(func.avg(GwyScoreLine.min_score)).scalar()

    def group_counts(column):
        rows = (
            base.with_entities(column, func.count(GwyScoreLine.id))
            .group_by(column)
            .order_by(func.count(GwyScoreLine.id).desc())
            .all()
        )
        return [
            GwyScoreLineStatsGroup(key=str(k), count=c)
            for k, c in rows
            if k is not None and str(k).strip() != ""
        ]

    return GwyScoreLineStatsResponse(
        total=total,
        avg_score=round(avg, 1) if avg is not None else None,
        by_batch=group_counts(GwyScoreLine.batch),
        by_year=group_counts(GwyScoreLine.year),
    )


@router.get("", response_model=GwyScoreLineListResponse)
def list_gwy_score_lines(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    year: Optional[int] = Query(None, description="招考年份（默认全部）"),
    batch: Optional[str] = Query(None, description="批次过滤（首批/调剂/补充录用）"),
    position_code: Optional[str] = Query(None, description="职位代码精确匹配（关联职位用）"),
    q: Optional[str] = Query(None, description="关键词（招录机关/职位名称 模糊匹配）"),
    db: Session = Depends(get_db),
):
    """获取国考进面分数线列表（公开）。"""
    query = db.query(GwyScoreLine)

    if year:
        query = query.filter(GwyScoreLine.year == year)
    if batch:
        query = query.filter(GwyScoreLine.batch == batch)
    if position_code:
        query = query.filter(GwyScoreLine.position_code == position_code)
    if q:
        pattern = f"%{escape_like(q)}%"
        query = query.filter(
            or_(
                GwyScoreLine.dept_name.ilike(pattern, escape="\\"),
                GwyScoreLine.position_name.ilike(pattern, escape="\\"),
            )
        )

    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(GwyScoreLine.min_score.desc(), GwyScoreLine.position_code)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return GwyScoreLineListResponse(
        items=[GwyScoreLineResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )
