# backend/app/api/community.py
"""社区毕业去向报告 API 路由。"""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.community import (
    AggregateQuery,
    AggregateResponse,
    CommunityReportResponse,
    CommunityStats,
    CommunitySubmit,
)
from app.services.community_service import (
    aggregate,
    delete_report,
    get_stats,
    list_my_reports_paginated,
    submit_report,
)

router = APIRouter(prefix="/api/community", tags=["社区数据"])


@router.post("/submit", response_model=CommunityReportResponse)
def submit(
    body: CommunitySubmit,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return submit_report(db, user.id, body)


@router.get("/my-reports", response_model=PaginatedResponse[CommunityReportResponse])
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


@router.post("/aggregate", response_model=AggregateResponse)
def aggregate_endpoint(
    body: AggregateQuery,
    db: Session = Depends(get_db),
):
    return aggregate(db, body.school, body.major, body.year)


@router.get("/stats", response_model=CommunityStats)
def stats(db: Session = Depends(get_db)):
    return get_stats(db)
