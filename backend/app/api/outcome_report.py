"""上岸报告 API — 提交、查询、统计、公开墙。"""
import logging
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.outcome_report import AdmissionPath, OutcomeReport, OutcomeType
from app.models.user import User
from app.schemas.outcome_report import (
    OutcomeReportCreate,
    OutcomeReportListResponse,
    OutcomeReportResponse,
    OutcomeStatsResponse,
)
from app.services.experience_post_service import create_from_outcome_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/outcome-report", tags=["上岸报告"])


@router.post("/submit", response_model=OutcomeReportResponse, status_code=status.HTTP_201_CREATED)
def submit_outcome_report(
    body: OutcomeReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = OutcomeReport(
        user_id=str(user.id),
        outcome_type=body.outcome_type,
        target_school=body.target_school,
        target_major=body.target_major,
        actual_school=body.actual_school,
        actual_major=body.actual_major,
        score_total=body.score_total,
        score_politics=body.score_politics,
        score_english=body.score_english,
        score_major1=body.score_major1,
        score_major2=body.score_major2,
        admission_path=body.admission_path,
        year=body.year,
        confidence_before=body.confidence_before,
        satisfaction_after=body.satisfaction_after,
        what_i_would_do_differently=body.what_i_would_do_differently,
        advice_for_others=body.advice_for_others,
        is_public=body.is_public,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # 飞轮护城河：提交上岸报告后自动生成经验贴草稿（失败不阻断主流程）
    try:
        draft = create_from_outcome_report(db, report)
        if draft:
            logger.info("上岸报告 %s 已生成经验贴草稿 %s", report.id, draft.id)
    except Exception as e:
        logger.warning("从上岸报告生成经验贴失败 report_id=%s: %s", report.id, e)

    return report


@router.get("/mine", response_model=OutcomeReportListResponse)
def get_my_reports(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = (
        db.query(OutcomeReport)
        .filter(OutcomeReport.user_id == str(user.id))
        .order_by(OutcomeReport.created_at.desc())
        .all()
    )
    return OutcomeReportListResponse(items=items, total=len(items))


@router.get("/school/{school_name}", response_model=OutcomeReportListResponse)
def get_reports_by_school(
    school_name: str,
    major: str | None = None,
    year: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(OutcomeReport).filter(
        OutcomeReport.is_public == "public",
        OutcomeReport.target_school.ilike(f"%{school_name}%"),
    )
    if major:
        q = q.filter(OutcomeReport.target_major.ilike(f"%{major}%"))
    if year:
        q = q.filter(OutcomeReport.year == year)
    total = q.count()
    items = (
        q.order_by(OutcomeReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return OutcomeReportListResponse(items=items, total=total)


@router.get("/stats/{school_name}/{major}", response_model=OutcomeStatsResponse)
def get_outcome_stats(
    school_name: str,
    major: str,
    db: Session = Depends(get_db),
):
    q = db.query(OutcomeReport).filter(
        OutcomeReport.is_public == "public",
        OutcomeReport.target_school.ilike(f"%{school_name}%"),
        OutcomeReport.target_major.ilike(f"%{major}%"),
    )
    reports = q.all()
    total = len(reports)
    if total == 0:
        return OutcomeStatsResponse(
            school=school_name,
            major=major,
            total_outcomes=0,
            score_distribution={},
            path_breakdown={},
            common_reflections=[],
        )

    accepted = sum(
        1 for r in reports
        if r.outcome_type in (OutcomeType.grad_civil_career, OutcomeType.adjustment)
    )
    acceptance_rate = round(accepted / total, 2) if total else 0

    scores = [r.score_total for r in reports if r.score_total is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else None

    # Score distribution buckets
    dist: dict[str, int] = {"350+": 0, "300-349": 0, "250-299": 0, "below_250": 0}
    for s in scores:
        if s >= 350:
            dist["350+"] += 1
        elif s >= 300:
            dist["300-349"] += 1
        elif s >= 250:
            dist["250-299"] += 1
        else:
            dist["below_250"] += 1

    # Path breakdown
    path_counter = Counter()
    for r in reports:
        path_counter[r.admission_path.value if hasattr(r.admission_path, "value") else r.admission_path] += 1
    path_breakdown = dict(path_counter)

    # Common reflections (top non-empty ones)
    reflections = [
        r.what_i_would_do_differently
        for r in reports
        if r.what_i_would_do_differently
    ]
    # Simple dedup by exact match
    seen = set()
    unique_reflections = []
    for ref in reflections:
        if ref not in seen:
            seen.add(ref)
            unique_reflections.append(ref)
    common_reflections = unique_reflections[:10]

    return OutcomeStatsResponse(
        school=school_name,
        major=major,
        total_outcomes=total,
        acceptance_rate=acceptance_rate,
        avg_score_total=avg_score,
        score_distribution=dist,
        path_breakdown=path_breakdown,
        common_reflections=common_reflections,
    )


@router.get("/landing-wall", response_model=OutcomeReportListResponse)
def get_landing_wall(
    school: str | None = None,
    major: str | None = None,
    year: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    q = db.query(OutcomeReport).filter(OutcomeReport.is_public == "public")
    if school:
        q = q.filter(OutcomeReport.target_school.ilike(f"%{school}%"))
    if major:
        q = q.filter(OutcomeReport.target_major.ilike(f"%{major}%"))
    if year:
        q = q.filter(OutcomeReport.year == year)
    total = q.count()
    items = (
        q.order_by(OutcomeReport.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return OutcomeReportListResponse(items=items, total=total)
