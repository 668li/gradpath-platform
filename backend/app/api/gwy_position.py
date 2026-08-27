"""国考职位 API — 公开只读：列表（筛选+分页）、详情、统计。

数据来源：2026 国考招考简章职位表（fetch_gwy_positions.py 采集），仅做查询展示。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.gwy_position import GwyPosition
from app.schemas.gwy_position import (
    GwyPositionListResponse,
    GwyPositionResponse,
    GwyPositionStatsGroup,
    GwyPositionStatsResponse,
)
from app.services.employment_service import escape_like

router = APIRouter(prefix="/api/gwy-positions", tags=["国考职位"])


@router.get("/stats", response_model=GwyPositionStatsResponse)
def gwy_position_stats(
    year: int | None = Query(None, description="招考年份（默认全部）"),
    db: Session = Depends(get_db),
):
    """国考职位统计：总数 + 按省份/学历/机构层级/考试类别分组计数。"""
    base = db.query(GwyPosition)
    if year:
        base = base.filter(GwyPosition.year == year)
    total = base.count()

    def group_counts(column):
        rows = (
            base.with_entities(column, func.count(GwyPosition.id))
            .group_by(column)
            .order_by(func.count(GwyPosition.id).desc())
            .all()
        )
        # 空值不参与分组展示（避免无意义的 null 桶）
        return [
            GwyPositionStatsGroup(key=str(k), count=c)
            for k, c in rows
            if k is not None and str(k).strip() != ""
        ]

    return GwyPositionStatsResponse(
        total=total,
        by_province=group_counts(GwyPosition.work_location),
        by_education=group_counts(GwyPosition.education_req),
        by_org_level=group_counts(GwyPosition.org_level),
        by_exam_category=group_counts(GwyPosition.exam_category),
    )


@router.get("", response_model=GwyPositionListResponse)
def list_gwy_positions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    q: str | None = Query(None, description="关键词（职位名称/部门/专业/内设机构 模糊匹配）"),
    education_req: str | None = Query(None, description="学历要求过滤（如：本科及以上）"),
    political_status: str | None = Query(None, description="政治面貌过滤（如：中共党员）"),
    org_level: str | None = Query(None, description="机构层级过滤"),
    exam_category: str | None = Query(None, description="考试类别过滤"),
    province: str | None = Query(None, description="省份前缀匹配（如：北京）"),
    position_code: str | None = Query(None, description="职位代码精确匹配"),
    year: int | None = Query(None, description="招考年份（默认全部）"),
    db: Session = Depends(get_db),
):
    """获取国考职位列表（公开）。"""
    query = db.query(GwyPosition)

    if year:
        query = query.filter(GwyPosition.year == year)
    if q:
        pattern = f"%{escape_like(q)}%"
        query = query.filter(
            or_(
                GwyPosition.position_name.ilike(pattern, escape="\\"),
                GwyPosition.dept_name.ilike(pattern, escape="\\"),
                GwyPosition.bureau.ilike(pattern, escape="\\"),
                GwyPosition.major_req.ilike(pattern, escape="\\"),
            )
        )
    if education_req:
        query = query.filter(GwyPosition.education_req == education_req)
    if political_status:
        query = query.filter(GwyPosition.political_status == political_status)
    if org_level:
        query = query.filter(GwyPosition.org_level == org_level)
    if exam_category:
        query = query.filter(GwyPosition.exam_category == exam_category)
    if province:
        query = query.filter(
            GwyPosition.work_location.like(f"{escape_like(province)}%", escape="\\")
        )
    if position_code:
        query = query.filter(GwyPosition.position_code == position_code)

    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(GwyPosition.dept_code, GwyPosition.position_code)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return GwyPositionListResponse(
        items=[GwyPositionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{position_id}", response_model=GwyPositionResponse)
def get_gwy_position_detail(
    position_id: str,
    db: Session = Depends(get_db),
):
    """获取国考职位详情。"""
    position = db.query(GwyPosition).filter(GwyPosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="职位不存在")
    return GwyPositionResponse.model_validate(position)
