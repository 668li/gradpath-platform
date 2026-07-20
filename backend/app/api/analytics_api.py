"""数据分析 API — 分数线趋势、录取率、报录比、调剂分析。"""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["数据分析"])


@router.get("/api/analytics/scoreline-trend")
def get_scoreline_trend(
    university: str = Query(..., description="院校名称"),
    major: str = Query(..., description="专业名称"),
    db: Session = Depends(get_db),
):
    """获取分数线多年趋势 — 公开接口。"""
    # 修复 ImportError: 实际路径为 app.services.analytics_service
    from app.services.analytics_service import get_analytics_service

    analytics = get_analytics_service(db)
    return analytics.get_scoreline_trend(university, major)


@router.get("/api/analytics/admission-rate")
def get_admission_rate(
    university: str | None = Query(None, description="院校名称"),
    major: str | None = Query(None, description="专业名称"),
    year: int | None = Query(None, description="年份"),
    db: Session = Depends(get_db),
):
    """获取录取率分析 — 公开接口。"""
    # 修复 ImportError: 实际路径为 app.services.analytics_service
    from app.services.analytics_service import get_analytics_service

    analytics = get_analytics_service(db)
    return analytics.get_admission_rate(university, major, year)


@router.get("/api/analytics/application-ratio")
def get_application_ratio(
    year: int | None = Query(None, description="年份"),
    top_n: int = Query(20, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_db),
):
    """获取报录比分析 — 公开接口。"""
    # 修复 ImportError: 实际路径为 app.services.analytics_service
    from app.services.analytics_service import get_analytics_service

    analytics = get_analytics_service(db)
    return analytics.get_application_ratio(year, top_n)


@router.get("/api/analytics/adjustment-success")
def get_adjustment_analysis(
    university: str | None = Query(None, description="院校名称"),
    db: Session = Depends(get_db),
):
    """获取调剂成功率分析 — 公开接口。"""
    # 修复 ImportError: 实际路径为 app.services.analytics_service
    from app.services.analytics_service import get_analytics_service

    analytics = get_analytics_service(db)
    return analytics.get_adjustment_analysis(university)
