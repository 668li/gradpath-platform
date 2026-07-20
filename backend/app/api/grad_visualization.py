"""考研数据可视化 API — 概览统计、分数趋势、院校对比。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.grad_intel import (
    GradAdjustmentInfo,
    GradSchoolIntel,
    GradScorelineRecord,
    GradYanzhaoProgram,
)

router = APIRouter(prefix="/api/grad-intel/visualization", tags=["考研可视化"])


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    """返回聚合统计：院校总数、专业总数、平均分数线。"""
    total_schools = db.query(
        func.count(func.distinct(GradSchoolIntel.school_name))
    ).scalar() or 0

    total_programs = db.query(
        func.count(func.distinct(GradYanzhaoProgram.major_name))
    ).scalar() or 0

    avg_scoreline = db.query(
        func.avg(GradScorelineRecord.total_score_line)
    ).scalar()

    return {
        "total_schools": total_schools,
        "total_programs": total_programs,
        "average_scoreline": round(avg_scoreline, 1) if avg_scoreline else None,
    }


@router.get("/score-trends")
def get_score_trends(
    university: str = Query(..., description="院校名称"),
    db: Session = Depends(get_db),
):
    """返回某院校的历年分数线趋势。"""
    records = (
        db.query(GradScorelineRecord)
        .filter(GradScorelineRecord.university_name == university)
        .order_by(GradScorelineRecord.year)
        .all()
    )

    if not records:
        return {"university": university, "years": [], "total_score_lines": []}

    years = []
    total_score_lines = []
    for r in records:
        if r.year not in years:
            years.append(r.year)
            total_score_lines.append(r.total_score_line)
        else:
            idx = years.index(r.year)
            if r.total_score_line and (
                total_score_lines[idx] is None
                or r.total_score_line < total_score_lines[idx]
            ):
                total_score_lines[idx] = r.total_score_line

    return {
        "university": university,
        "years": years,
        "total_score_lines": total_score_lines,
    }


@router.get("/school-comparison")
def get_school_comparison(
    universities: str = Query(..., description="逗号分隔的院校名称列表"),
    db: Session = Depends(get_db),
):
    """返回多所院校的对比数据。"""
    names = [n.strip() for n in universities.split(",") if n.strip()]
    results = []

    for name in names:
        latest_record = (
            db.query(GradScorelineRecord)
            .filter(GradScorelineRecord.university_name == name)
            .order_by(GradScorelineRecord.year.desc())
            .first()
        )
        program_count = (
            db.query(func.count(GradYanzhaoProgram.id))
            .filter(GradYanzhaoProgram.university_name == name)
            .scalar()
        ) or 0
        adjustment_count = (
            db.query(func.count(GradAdjustmentInfo.id))
            .filter(GradAdjustmentInfo.university_name == name)
            .scalar()
        ) or 0

        results.append({
            "university_name": name,
            "latest_year": latest_record.year if latest_record else None,
            "latest_scoreline": latest_record.total_score_line if latest_record else None,
            "program_count": program_count,
            "adjustment_count": adjustment_count,
        })

    return {"schools": results}


@router.get("/score-distribution")
def get_score_distribution(
    tier: str | None = Query(None, description="按院校层次过滤"),
    db: Session = Depends(get_db),
):
    """返回分数线分布数据，按层次分组统计。"""
    query = db.query(
        GradScorelineRecord.university_name,
        GradScorelineRecord.total_score_line,
        GradScorelineRecord.year,
    )
    if tier:
        query = query.join(
            GradSchoolIntel,
            GradScorelineRecord.university_name == GradSchoolIntel.school_name,
        ).filter(GradSchoolIntel.school_tier == tier)

    records = query.filter(
        GradScorelineRecord.total_score_line.isnot(None)
    ).order_by(GradScorelineRecord.year.desc()).limit(500).all()

    if not records:
        return {"tiers": {}, "distribution": []}

    # 按最近一年的分数分桶
    latest_year = max(r.year for r in records) if records else None
    latest_records = [r for r in records if r.year == latest_year]

    buckets = {"<300": 0, "300-349": 0, "350-399": 0, "400-449": 0, "450+": 0}
    for r in latest_records:
        s = r.total_score_line
        if s < 300:
            buckets["<300"] += 1
        elif s < 350:
            buckets["300-349"] += 1
        elif s < 400:
            buckets["350-399"] += 1
        elif s < 450:
            buckets["400-449"] += 1
        else:
            buckets["450+"] += 1

    distribution = [{"range": k, "count": v} for k, v in buckets.items()]

    return {
        "latest_year": latest_year,
        "total_records": len(latest_records),
        "distribution": distribution,
    }


@router.get("/crawler-quality")
def get_crawler_quality(db: Session = Depends(get_db)):
    """返回爬虫数据质量指标。"""
    from app.models.crawler_run import CrawlerRun

    recent_runs = (
        db.query(CrawlerRun)
        .order_by(CrawlerRun.created_at.desc())
        .limit(50)
        .all()
    )

    total_runs = len(recent_runs)
    success_runs = sum(1 for r in recent_runs if r.status == "success")
    failed_runs = sum(1 for r in recent_runs if r.status == "failed")
    total_fetched = sum(r.items_fetched or 0 for r in recent_runs)
    total_stored = sum(r.items_stored or 0 for r in recent_runs)
    total_duplicates = sum(r.items_duplicates or 0 for r in recent_runs)
    total_errors = sum(r.error_count or 0 for r in recent_runs)

    dedup_rate = round(total_duplicates / total_fetched * 100, 1) if total_fetched > 0 else 0
    success_rate = round(success_runs / total_runs * 100, 1) if total_runs > 0 else 0
    store_rate = round(total_stored / total_fetched * 100, 1) if total_fetched > 0 else 0

    return {
        "total_runs": total_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "success_rate": success_rate,
        "total_fetched": total_fetched,
        "total_stored": total_stored,
        "total_duplicates": total_duplicates,
        "dedup_rate": dedup_rate,
        "store_rate": store_rate,
        "total_errors": total_errors,
    }
