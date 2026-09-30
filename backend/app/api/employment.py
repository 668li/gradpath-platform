# backend/app/api/employment.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.core.cursor_pagination import apply_cursor_filter, encode_cursor
from app.database import get_db
from app.models.ingestion import ExternalResearchItem
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School
from app.schemas.common import CursorPaginatedResponse
from app.schemas.employment import (
    EmploymentAnnounceItem,
    EmploymentAnnounceListResponse,
    EmploymentSearchResponse,
    EmploymentStatsResponse,
    MajorQuery,
    MarketOverviewResponse,
    SchoolResponse,
    SearchBody,
)
from app.services.employment_service import (
    get_stats,
    list_majors,
    list_schools,
    market_overview,
    search_employment,
)

router = APIRouter(prefix="/api/employment", tags=["就业数据"])


@router.get("/market-overview", response_model=MarketOverviewResponse)
def market_overview_endpoint(db: Session = Depends(get_db)):
    """就业市场概览（B4）：companies/salary_benchmarks 真实聚合+覆盖度如实标注。"""
    return market_overview(db)


@router.get("/search", response_model=EmploymentSearchResponse)
def search(
    school: str = Query(..., description="学校名称（模糊匹配）"),
    major: str = Query(..., description="专业名称（模糊匹配）"),
    year: int | None = Query(None, description="年份筛选"),
    degree: str | None = Query(None, description="学历筛选"),
    db: Session = Depends(get_db),
):
    return search_employment(db, school, major, year, degree)


@router.post("/search", response_model=EmploymentSearchResponse)
def search_post(body: SearchBody, db: Session = Depends(get_db)):
    return search_employment(db, body.school, body.major, body.year, body.degree)


@router.get("/schools", response_model=list[SchoolResponse])
def schools(db: Session = Depends(get_db)):
    return list_schools(db)


@router.get("/schools/cursor", response_model=CursorPaginatedResponse[SchoolResponse])
def schools_cursor(
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    cursor: str | None = Query(None, description="游标（cursor 分页）"),
    db: Session = Depends(get_db),
):
    """游标分页获取院校列表（适合无限滚动，避免深页性能退化）。

    仅返回有已发布报告的院校，按 (created_at, id) 倒序排列。
    """
    # EXISTS 子查询而非 JOIN+DISTINCT：School 含 json 列，PG 的 json 类型无
    # equality operator，对全行 DISTINCT 直接 500（2026-09-30 生产实测）。
    query = db.query(School).filter(
        exists().where(
            ReportRecord.school_id == School.id,
            ReportRecord.parse_status == ParseStatus.published,
        )
    )
    query = apply_cursor_filter(query, cursor, time_col=School.created_at, id_col=School.id)
    # id 决胜键：同 created_at 行的页界必须确定（否则游标翻页重复/漏行）
    items = query.order_by(School.created_at.desc(), School.id.desc()).limit(page_size + 1).all()
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]
    next_cursor = (
        encode_cursor(items[-1].created_at, str(items[-1].id)) if has_more and items else None
    )
    # School ORM 模型无 report_count/major_count 字段，SchoolResponse 又未声明
    # from_attributes=True；这里手动构造 dict，与 list_schools 行为一致。
    resp_items = [
        SchoolResponse(
            id=str(s.id),
            name=s.name,
            slug=s.slug,
            code=s.code,
            report_count=0,
            major_count=0,
        )
        for s in items
    ]
    return CursorPaginatedResponse(
        items=resp_items,
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/majors", response_model=list[str])
def majors(school: str = Query(...), db: Session = Depends(get_db)):
    return list_majors(db, school)


@router.post("/majors", response_model=list[str])
def majors_post(body: MajorQuery, db: Session = Depends(get_db)):
    return list_majors(db, body.school)


@router.get("/announces", response_model=EmploymentAnnounceListResponse)
def employment_announces(
    page: int = Query(1, ge=1, le=1000),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """公开只读：已审核通过的高校就业网官方公告（EMP-3，2026-09-30）。

    - 过滤 ExternalResearchItem（item_type=employment_announce ∧ review_status=APPROVED）；
      PENDING/REJECTED 条目永不出现（审核闸纪律）。
    - 只出 title/source_url/source_name/published_at/credibility 非敏感字段；
      排序=created_time 倒序（公告发布日期存 external_meta，采集时间与其单调一致）。
    """
    query = db.query(ExternalResearchItem).filter(
        ExternalResearchItem.item_type == "employment_announce",
        ExternalResearchItem.review_status == "APPROVED",
    )
    total = query.count()
    rows = (
        query.order_by(ExternalResearchItem.created_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return EmploymentAnnounceListResponse(
        total=total,
        items=[
            EmploymentAnnounceItem(
                title=it.title,
                source_url=it.source_url,
                source_name=(it.external_meta or {}).get("source_name"),
                published_at=(it.external_meta or {}).get("published_at"),
                credibility=it.credibility,
            )
            for it in rows
        ],
    )


@router.get("/stats", response_model=EmploymentStatsResponse)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)
