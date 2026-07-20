"""AI 推荐 API — 院校推荐、调剂推荐、暗知识推荐（公开接口）。"""
import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.recommendation import ContentBasedRecommender

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommend", tags=["AI 推荐"])


@router.get("/schools")
def recommend_schools(
    response: Response,
    target_score: int | None = Query(None, description="目标分数"),
    target_tier: str | None = Query(None, description="目标层次: 985/211/双一流/普通"),
    target_region: str | None = Query(None, description="目标地区"),
    target_major: str | None = Query(None, description="目标专业"),
    top_n: int = Query(10, ge=1, le=50, description="返回前 N 条"),
    db: Session = Depends(get_db),
):
    """推荐匹配的院校（公开接口，3分钟缓存）。"""
    recommender = ContentBasedRecommender(db)
    results = recommender.recommend_schools(
        target_score=target_score,
        target_tier=target_tier,
        target_region=target_region,
        target_major=target_major,
        top_n=top_n,
    )
    response.headers["Cache-Control"] = "public, max-age=180"
    return {
        "items": [asdict(r) for r in results],
        "total": len(results),
    }


@router.get("/adjustments")
def recommend_adjustments(
    target_score: int | None = Query(None, description="目标分数"),
    target_major: str | None = Query(None, description="目标专业"),
    target_region: str | None = Query(None, description="目标地区"),
    top_n: int = Query(10, ge=1, le=50, description="返回前 N 条"),
    db: Session = Depends(get_db),
):
    """推荐调剂机会（公开接口，5分钟缓存）。"""
    recommender = ContentBasedRecommender(db)
    results = recommender.recommend_adjustments(
        target_score=target_score,
        target_major=target_major,
        target_region=target_region,
        top_n=top_n,
    )
    return {
        "items": [asdict(r) for r in results],
        "total": len(results),
    }


@router.get("/dark-knowledge")
def recommend_dark_knowledge(
    stage: str | None = Query(None, description="备考阶段: decision/school_selection/preparation/exam/retest/transfer"),
    top_n: int = Query(10, ge=1, le=50, description="返回前 N 条"),
    db: Session = Depends(get_db),
):
    """推荐暗知识（公开接口，5分钟缓存）。"""
    recommender = ContentBasedRecommender(db)
    results = recommender.recommend_dark_knowledge(
        stage=stage,
        top_n=top_n,
    )
    return {
        "items": [asdict(r) for r in results],
        "total": len(results),
    }
