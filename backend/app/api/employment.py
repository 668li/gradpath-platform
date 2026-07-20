# backend/app/api/employment.py
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.cursor_pagination import apply_cursor_filter, encode_cursor
from app.database import get_db
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School
from app.schemas.common import CursorPaginatedResponse
from app.schemas.employment import (
    EmploymentSearchResponse,
    EmploymentStatsResponse,
    MajorQuery,
    SchoolResponse,
    SearchBody,
)
from app.services.employment_service import get_stats, list_majors, list_schools, search_employment

router = APIRouter(prefix="/api/employment", tags=["就业数据"])


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
    cursor: Optional[str] = Query(None, description="游标（cursor 分页）"),
    db: Session = Depends(get_db),
):
    """游标分页获取院校列表（适合无限滚动，避免深页性能退化）。

    仅返回有已发布报告的院校，按 (created_at, id) 倒序排列。
    """
    query = (
        db.query(School)
        .join(ReportRecord, ReportRecord.school_id == School.id)
        .filter(ReportRecord.parse_status == ParseStatus.published)
        .distinct()
    )
    query = apply_cursor_filter(
        query, cursor, time_col=School.created_at, id_col=School.id
    )
    items = query.order_by(School.created_at.desc()).limit(page_size + 1).all()
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]
    next_cursor = (
        encode_cursor(items[-1].created_at, str(items[-1].id))
        if has_more and items
        else None
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


@router.get("/stats", response_model=EmploymentStatsResponse)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)
