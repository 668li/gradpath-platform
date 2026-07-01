# backend/app/api/interview.py
"""公司面试经验报告 API 路由。"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.interview import (
    CompanyQuery,
    InterviewAggregateQuery,
    InterviewAggregateResponse,
    InterviewReportResponse,
    InterviewStats,
    InterviewSubmit,
)
from app.services.interview_service import (
    aggregate,
    delete_report,
    get_stats,
    list_companies,
    list_my_reports_paginated,
    submit_report,
)

router = APIRouter(prefix="/api/interview", tags=["面试经验"])


@router.post("/submit", response_model=InterviewReportResponse)
def submit(
    body: InterviewSubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return submit_report(db, user.id, body)


@router.get("/my-reports", response_model=PaginatedResponse[InterviewReportResponse])
def my_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items, total = list_my_reports_paginated(db, user.id, page, page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    report_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    delete_report(db, user.id, report_id)


@router.post("/aggregate", response_model=InterviewAggregateResponse)
def aggregate_endpoint(
    body: InterviewAggregateQuery,
    db: Session = Depends(get_db),
):
    return aggregate(db, body.company, body.position)


@router.get("/stats", response_model=InterviewStats)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)


@router.post("/companies", response_model=list[dict])
def companies(
    body: CompanyQuery,
    db: Session = Depends(get_db),
):
    return list_companies(db, body.keyword)
