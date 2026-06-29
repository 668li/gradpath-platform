# backend/app/api/community.py
"""社区毕业去向报告 API 路由。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
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
    get_my_reports,
    get_stats,
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


@router.get("/my-reports", response_model=list[CommunityReportResponse])
def my_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return get_my_reports(db, user.id)


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
