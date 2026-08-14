"""复盘中心 API — 全量做实（鉴权 + 幂等 + AI 降级）。

路径与 DTO 对齐系统设计 §3.2.M4.2 接口清单；
user_id 一律由登录态 token 推断（get_current_user），不在请求体传。
"""
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.review import (
    AIReviewRequest,
    AIReviewVO,
    ReviewCreateRequest,
    ReviewDetailVO,
    ReviewPageResponse,
    ReviewVO,
)
from app.services import review_service

router = APIRouter(prefix="/api/reviews", tags=["复盘中心"])


@router.post("", response_model=ReviewVO)
def create_review(
    body: ReviewCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """创建复盘记录（幂等：X-Idempotency-Key → biz_req_no）。"""
    review = review_service.create_review(
        db, user.id, body, idempotency_key=x_idempotency_key
    )
    return ReviewVO.model_validate(review)


@router.get("/{review_id}", response_model=ReviewDetailVO)
def get_review_detail(
    review_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读取复盘详情（含 AI 分析字段）。"""
    review = review_service.get_review(db, user.id, review_id)
    return ReviewDetailVO.model_validate(review)


@router.get("", response_model=ReviewPageResponse)
def list_reviews(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    size: int = Query(20, ge=1, le=100, description="每页条数"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """复盘列表（分页）。"""
    items, total = review_service.list_reviews(db, user.id, page=page, size=size)
    return ReviewPageResponse(
        items=[ReviewVO.model_validate(r) for r in items], total=total
    )


@router.post("/{review_id}/ai-analyze", response_model=AIReviewVO)
async def ai_analyze_review(
    review_id: int,
    body: AIReviewRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """触发 AI 复盘分析（LLM 不可用走模板降级；已分析返回既有结果）。"""
    review = await review_service.ai_analyze_review(
        db,
        user.id,
        review_id,
        focus_areas=body.focus_areas,
        temperature=body.temperature,
    )
    return review_service.to_ai_vo(review)


@router.get("/{review_id}/ai-result", response_model=AIReviewVO)
def get_ai_review_result(
    review_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取 AI 复盘结果。"""
    review = review_service.get_review(db, user.id, review_id)
    return review_service.to_ai_vo(review)
