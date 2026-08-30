"""省考职位 API — 公开只读：列表（筛选+分页）、详情、统计。

数据来源：各省公务员考试招录职位表（fetch_gd_shengkao_positions.py 采集，首例：广东省 2026），仅做查询展示。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.database import get_db
from app.models.gwy_province_position import GwyProvincePosition
from app.schemas.gwy_province_position import (
    GwyProvincePositionListResponse,
    GwyProvincePositionResponse,
    GwyProvincePositionStatsGroup,
    GwyProvincePositionStatsResponse,
)
from app.services.employment_service import escape_like

router = APIRouter(prefix="/api/gwy-province-positions", tags=["省考职位"])


@router.get("/stats", response_model=GwyProvincePositionStatsResponse)
def gwy_province_position_stats(
    year: int | None = Query(None, description="招考年份（默认全部）"),
    province: str | None = Query(None, description="省份（默认全部，如：广东）"),
    db: Session = Depends(get_db),
):
    """省考职位统计：总数 + 按招录系统/学历/考区/应届限制分组，含总招录人数。

    筛选选项一天不变，6 个聚合查询走 5 分钟缓存（原每次请求都全表聚合）。
    """
    cache_key = f"gwyprov:stats:{year or 'all'}:{province or 'all'}"
    cached = cache.get(cache_key)
    if cached is not None:
        return GwyProvincePositionStatsResponse.model_validate(cached)

    base = db.query(GwyProvincePosition)
    if year:
        base = base.filter(GwyProvincePosition.year == year)
    if province:
        base = base.filter(GwyProvincePosition.province == province)
    total = base.count()
    total_recruit = base.with_entities(func.sum(GwyProvincePosition.recruit_count)).scalar()

    def group_counts(column):
        rows = (
            base.with_entities(column, func.count(GwyProvincePosition.id))
            .group_by(column)
            .order_by(func.count(GwyProvincePosition.id).desc())
            .all()
        )
        # 空值不参与分组展示（避免无意义的 null 桶）
        return [
            GwyProvincePositionStatsGroup(key=str(k), count=c)
            for k, c in rows
            if k is not None and str(k).strip() != ""
        ]

    response = GwyProvincePositionStatsResponse(
        total=total,
        total_recruit=total_recruit or 0,
        by_sheet=group_counts(GwyProvincePosition.sheet_name),
        by_education=group_counts(GwyProvincePosition.education_req),
        by_region=group_counts(GwyProvincePosition.exam_region),
        by_fresh_grad_only=group_counts(GwyProvincePosition.fresh_grad_only),
    )
    cache.set(cache_key, response.model_dump(), ttl=300)
    return response


@router.get("", response_model=GwyProvincePositionListResponse)
def list_gwy_province_positions(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    q: str | None = Query(None, description="关键词（职位名称/招考单位/职位简介/专业 模糊匹配）"),
    province: str | None = Query(None, description="省份过滤（如：广东）"),
    year: int | None = Query(None, description="招考年份（默认全部）"),
    exam_region: str | None = Query(None, description="考区过滤（如：广州）"),
    education_req: str | None = Query(None, description="学历要求过滤（如：本科）"),
    position_type: str | None = Query(None, description="职位类别过滤（如：综合管理类）"),
    fresh_grad_only: str | None = Query(None, description="是否限应届毕业生报考（是/否）"),
    position_code: str | None = Query(None, description="职位代码精确匹配"),
    sheet_name: str | None = Query(None, description="招录系统过滤（如：县以上机关）"),
    db: Session = Depends(get_db),
):
    """获取省考职位列表（公开）。"""
    query = db.query(GwyProvincePosition)

    if year:
        query = query.filter(GwyProvincePosition.year == year)
    if province:
        query = query.filter(GwyProvincePosition.province == province)
    if q:
        pattern = f"%{escape_like(q)}%"
        query = query.filter(
            or_(
                GwyProvincePosition.position_name.ilike(pattern, escape="\\"),
                GwyProvincePosition.dept_name.ilike(pattern, escape="\\"),
                GwyProvincePosition.position_desc.ilike(pattern, escape="\\"),
                GwyProvincePosition.major_req_grad.ilike(pattern, escape="\\"),
                GwyProvincePosition.major_req_undergrad.ilike(pattern, escape="\\"),
                GwyProvincePosition.major_req_junior.ilike(pattern, escape="\\"),
            )
        )
    if exam_region:
        query = query.filter(GwyProvincePosition.exam_region == exam_region)
    if education_req:
        query = query.filter(GwyProvincePosition.education_req == education_req)
    if position_type:
        query = query.filter(GwyProvincePosition.position_type == position_type)
    if fresh_grad_only:
        query = query.filter(GwyProvincePosition.fresh_grad_only == fresh_grad_only)
    if position_code:
        query = query.filter(GwyProvincePosition.position_code == position_code)
    if sheet_name:
        query = query.filter(GwyProvincePosition.sheet_name == sheet_name)

    total = query.count()
    offset = (page - 1) * page_size
    items = (
        query.order_by(GwyProvincePosition.dept_code, GwyProvincePosition.position_code)
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return GwyProvincePositionListResponse(
        items=[GwyProvincePositionResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{position_id}", response_model=GwyProvincePositionResponse)
def get_gwy_province_position_detail(
    position_id: str,
    db: Session = Depends(get_db),
):
    """获取省考职位详情。"""
    position = db.query(GwyProvincePosition).filter(GwyProvincePosition.id == position_id).first()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="职位不存在")
    return GwyProvincePositionResponse.model_validate(position)
