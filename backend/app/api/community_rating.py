"""社区评分 API — 经验贴/知识文章的质量信号与已上岸徽章。"""
import logging
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.community_rating import CommunityRating
from app.models.experience_post import ExperiencePost
from app.models.knowledge_article import KnowledgeArticle
from app.models.outcome_report import OutcomeReport
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/community-rating", tags=["社区评分"])

# 延迟导入 limiter 以避免循环导入
_limiter = None


def _get_limiter():
    global _limiter
    if _limiter is None:
        from app.main import limiter
        _limiter = limiter
    return _limiter


# ======================================================================
# Schema 定义
# ======================================================================

class RateRequest(BaseModel):
    """评分请求。"""
    target_type: str = Field(..., description="目标类型: experience_post / knowledge_article")
    target_id: UUID = Field(..., description="目标 ID")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    review: str | None = Field(None, max_length=2000, description="评论")


class RatingResponse(BaseModel):
    """评分响应。"""
    id: UUID
    user_id: UUID
    target_type: str
    target_id: UUID
    rating: int
    review: str | None
    created_at: str


class RatingStats(BaseModel):
    """评分统计。"""
    avg_stars: float
    rating_count: int
    quality_score: float
    distribution: dict  # {1: count, 2: count, ...}


class TopRatedItem(BaseModel):
    """高评分内容。"""
    target_id: UUID
    target_type: str
    title: str
    avg_stars: float
    rating_count: int
    quality_score: float


class UserRatingHistory(BaseModel):
    """用户评分历史。"""
    ratings: list[RatingResponse]
    total_ratings: int
    avg_rating_given: float


class BadgeVerifyRequest(BaseModel):
    """已上岸徽章验证请求。"""
    outcome_report_id: UUID = Field(..., description="上岸报告 ID")


class BadgeResponse(BaseModel):
    """徽章验证响应。"""
    badge_granted: bool
    message: str
    badge_type: str | None = None


# ======================================================================
# 评分端点
# ======================================================================

@router.post("/rate", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
@_get_limiter().limit("20/minute")
def rate_content(
    request: Request,
    response: Response,
    body: RateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """评分经验贴或知识文章（需登录）。

    每个用户对每个目标只能评一次，重复评分将更新。
    """
    try:
        # 验证目标存在
        if body.target_type == "experience_post":
            target = db.query(ExperiencePost).filter(ExperiencePost.id == body.target_id).first()
            if not target:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="经验贴不存在")
        elif body.target_type == "knowledge_article":
            target = db.query(KnowledgeArticle).filter(KnowledgeArticle.id == body.target_id).first()
            if not target:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="知识文章不存在")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的 target_type")

        # 检查是否已评过分（更新 or 新建）
        existing = (
            db.query(CommunityRating)
            .filter(
                CommunityRating.user_id == user.id,
                CommunityRating.target_type == body.target_type,
                CommunityRating.target_id == body.target_id,
            )
            .first()
        )

        if existing:
            existing.rating = body.rating
            existing.review = body.review
            db.commit()
            db.refresh(existing)
            rating = existing
        else:
            rating = CommunityRating(
                user_id=user.id,
                target_type=body.target_type,
                target_id=body.target_id,
                rating=body.rating,
                review=body.review,
            )
            db.add(rating)
            db.commit()
            db.refresh(rating)

        return RatingResponse(
            id=rating.id,
            user_id=rating.user_id,
            target_type=rating.target_type,
            target_id=rating.target_id,
            rating=rating.rating,
            review=rating.review,
            created_at=rating.created_at.isoformat() if rating.created_at else "",
        )
    except HTTPException:
        raise
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("rate_content failed")
        raise HTTPException(status_code=500, detail="评分失败，请稍后重试")


@router.get("/top", response_model=list[TopRatedItem])
@_get_limiter().limit("30/minute")
def get_top_rated(
    request: Request,
    response: Response,
    target_type: str = Query("experience_post", description="目标类型"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    db: Session = Depends(get_db),
):
    """获取高评分内容列表。

    排序使用 quality_score = avg_stars * log(1 + rating_count)。
    """
    # 聚合评分
    stats = (
        db.query(
            CommunityRating.target_id,
            func.avg(CommunityRating.rating).label("avg_stars"),
            func.count(CommunityRating.id).label("rating_count"),
        )
        .filter(CommunityRating.target_type == target_type)
        .group_by(CommunityRating.target_id)
        .having(func.count(CommunityRating.id) >= 1)
        .all()
    )

    # 计算 quality_score 并排序
    items = []
    for row in stats:
        avg_stars = float(row.avg_stars)
        rating_count = row.rating_count
        quality_score = avg_stars * math.log(1 + rating_count)
        items.append({
            "target_id": row.target_id,
            "avg_stars": round(avg_stars, 2),
            "rating_count": rating_count,
            "quality_score": round(quality_score, 2),
        })

    items.sort(key=lambda x: x["quality_score"], reverse=True)
    items = items[:limit]

    # 批量查询标题，避免 N+1
    target_ids = [item["target_id"] for item in items]
    title_map: dict = {}
    if target_ids:
        if target_type == "experience_post":
            rows = (
                db.query(ExperiencePost.id, ExperiencePost.title)
                .filter(ExperiencePost.id.in_(target_ids))
                .all()
            )
            title_map = {r.id: r.title or "" for r in rows}
        elif target_type == "knowledge_article":
            rows = (
                db.query(KnowledgeArticle.id, KnowledgeArticle.title)
                .filter(KnowledgeArticle.id.in_(target_ids))
                .all()
            )
            title_map = {r.id: r.title or "" for r in rows}

    result = [
        TopRatedItem(
            target_id=item["target_id"],
            target_type=target_type,
            title=title_map.get(item["target_id"], ""),
            avg_stars=item["avg_stars"],
            rating_count=item["rating_count"],
            quality_score=item["quality_score"],
        )
        for item in items
    ]

    return result


@router.get("/user/{user_id}", response_model=UserRatingHistory)
@_get_limiter().limit("30/minute")
def get_user_ratings(
    request: Request,
    response: Response,
    user_id: UUID,
    db: Session = Depends(get_db),
):
    """获取用户的评分历史。"""
    ratings = (
        db.query(CommunityRating)
        .filter(CommunityRating.user_id == user_id)
        .order_by(CommunityRating.created_at.desc())
        .limit(100)
        .all()
    )

    rating_list = [
        RatingResponse(
            id=r.id,
            user_id=r.user_id,
            target_type=r.target_type,
            target_id=r.target_id,
            rating=r.rating,
            review=r.review,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in ratings
    ]

    avg_rating = sum(r.rating for r in ratings) / len(ratings) if ratings else 0

    return UserRatingHistory(
        ratings=rating_list,
        total_ratings=len(ratings),
        avg_rating_given=round(avg_rating, 2),
    )


@router.post("/verify-badge", response_model=BadgeResponse)
@_get_limiter().limit("5/minute")
def verify_badge(
    request: Request,
    response: Response,
    body: BadgeVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """验证"已上岸"徽章 — 需提交已通过审核的上岸报告。

    验证条件：
    1. 上岸报告属于当前用户
    2. 上岸报告 outcome_type 为 grad_civil_career
    3. 报告包含具体分数
    """
    try:
        report = (
            db.query(OutcomeReport)
            .filter(
                OutcomeReport.id == body.outcome_report_id,
                OutcomeReport.user_id == user.id,
            )
            .first()
        )

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上岸报告不存在或不属于当前用户",
            )

        # 验证条件
        if report.outcome_type.value != "grad_civil_career":
            return BadgeResponse(
                badge_granted=False,
                message="只有考研上岸报告可申请已上岸徽章",
            )

        if report.score_total is None:
            return BadgeResponse(
                badge_granted=False,
                message="上岸报告需包含具体分数才能验证",
            )

        # 授予徽章
        # 注意：这里只返回验证结果，实际徽章授予由 gamification 系统处理
        return BadgeResponse(
            badge_granted=True,
            message="已上岸徽章验证通过！请前往个人中心查看。",
            badge_type="已上岸",
        )
    except HTTPException:
        raise
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("verify_badge failed")
        raise HTTPException(status_code=500, detail="徽章验证失败，请稍后重试")


@router.get("/stats/{target_type}/{target_id}", response_model=RatingStats)
@_get_limiter().limit("30/minute")
def get_rating_stats(
    request: Request,
    response: Response,
    target_type: str,
    target_id: UUID,
    db: Session = Depends(get_db),
):
    """获取目标内容的评分统计。"""
    stats = (
        db.query(
            func.avg(CommunityRating.rating).label("avg_stars"),
            func.count(CommunityRating.id).label("rating_count"),
        )
        .filter(
            CommunityRating.target_type == target_type,
            CommunityRating.target_id == target_id,
        )
        .first()
    )

    avg_stars = float(stats.avg_stars) if stats.avg_stars else 0
    rating_count = stats.rating_count or 0
    quality_score = avg_stars * math.log(1 + rating_count) if rating_count > 0 else 0

    # 一次 GROUP BY 查询获取所有评分档位的分布，避免 5 次查询
    dist_rows = (
        db.query(CommunityRating.rating, func.count(CommunityRating.id))
        .filter(
            CommunityRating.target_type == target_type,
            CommunityRating.target_id == target_id,
        )
        .group_by(CommunityRating.rating)
        .all()
    )
    distribution = {str(i): 0 for i in range(1, 6)}
    for rating_val, cnt in dist_rows:
        distribution[str(rating_val)] = cnt or 0

    return RatingStats(
        avg_stars=round(avg_stars, 2),
        rating_count=rating_count,
        quality_score=round(quality_score, 2),
        distribution=distribution,
    )
