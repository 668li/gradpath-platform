"""考研数据可视化 API — 爬虫数据质量指标。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(prefix="/api/grad-intel/visualization", tags=["考研可视化"])


@router.get("/crawler-quality")
def get_crawler_quality(db: Session = Depends(get_db)):
    """返回爬虫数据质量指标。"""
    from app.models.crawler_run import CrawlerRun

    recent_runs = db.query(CrawlerRun).order_by(CrawlerRun.created_at.desc()).limit(50).all()

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
