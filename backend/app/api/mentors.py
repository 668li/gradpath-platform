"""AI 导师人格库 API — 多视角分析。"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.exceptions import BusinessError, ForbiddenError, NotFoundError, ValidationFailedError
from app.services import mentor_persona_service

router = APIRouter(prefix="/api/mentors", tags=["AI导师人格库"])


class MentorAdviceRequest(BaseModel):
    persona_code: str
    question: str
    user_context: str = ""


class MultiPerspectiveRequest(BaseModel):
    persona_codes: list[str]
    question: str
    user_context: str = ""


class MentorBatchRequest(BaseModel):
    """批量获取导师信息请求体。"""

    ids: list[str] = Field(
        ..., min_length=1, max_length=100, description="导师 ID 列表（最多 100 个）"
    )


@router.get("/personas")
def list_personas():
    """列出所有导师人格。"""
    return mentor_persona_service.get_all_personas()


@router.post("/advice")
async def get_advice(body: MentorAdviceRequest):
    """获取单个导师视角的建议。"""
    # 修复 bug: service 层 raise ValueError("未知导师人格") -> 500，应转 422
    try:
        advice = await mentor_persona_service.get_mentor_advice(
            body.persona_code, body.question, body.user_context
        )
    except ValueError as e:
        raise ValidationFailedError(str(e)) from e
    return {
        "persona_code": body.persona_code,
        "advice": advice,
    }


@router.post("/multi-perspective")
async def get_multi_perspective(body: MultiPerspectiveRequest):
    """获取多个导师视角的建议（同一问题，不同角度）。"""
    # 修复 bug: 同上，未知 persona 应转 422
    try:
        results = await mentor_persona_service.get_multi_perspective(
            body.persona_codes, body.question, body.user_context
        )
    except ValueError as e:
        raise ValidationFailedError(str(e)) from e
    return {"perspectives": results}


# ============================================================================
# 考研导师评价系统 API
# ============================================================================
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.mentor import (
    MentorCreate,
    MentorListResponse,
    MentorResponse,
    MentorReviewCreate,
    MentorReviewListResponse,
    MentorReviewResponse,
    MentorUpdate,
)
from app.schemas.common import CursorPaginatedResponse
from app.services.mentor_service import (
    approve_review,
    check_duplicate_review,
    create_mentor,
    create_mentor_review,
    get_mentor,
    get_mentor_reviews,
    get_mentors,
    like_review,
    reject_review,
    update_mentor,
)


# === 导师查询 API ===

@router.get("/kaoyan-mentors", response_model=MentorListResponse, tags=["考研导师评价"])
def list_kaoyan_mentors(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    university: Optional[str] = Query(None, description="院校筛选"),
    department: Optional[str] = Query(None, description="院系筛选"),
    research_direction: Optional[str] = Query(None, description="研究方向筛选"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="最低评分"),
    enrollment_status: Optional[str] = Query(None, description="招生状态"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """获取考研导师列表（支持多维度筛选）"""
    mentors, total = get_mentors(
        db,
        page=page,
        page_size=page_size,
        university=university,
        department=department,
        research_direction=research_direction,
        min_rating=min_rating,
        enrollment_status=enrollment_status,
        search=search,
    )
    return MentorListResponse(
        items=[MentorResponse.model_validate(m) for m in mentors],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/kaoyan-mentors/cursor", response_model=CursorPaginatedResponse[MentorResponse], tags=["考研导师评价"])
def list_kaoyan_mentors_cursor(
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    cursor: Optional[str] = Query(None, description="游标（cursor 分页）"),
    university: Optional[str] = Query(None, description="院校筛选"),
    department: Optional[str] = Query(None, description="院系筛选"),
    research_direction: Optional[str] = Query(None, description="研究方向筛选"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="最低评分"),
    enrollment_status: Optional[str] = Query(None, description="招生状态"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """游标分页获取导师列表（适合无限滚动，避免深页性能退化）。

    按 (created_at, id) 倒序排列，前端传 next_cursor 即可获取下一页。
    """
    from app.core.cursor_pagination import apply_cursor_filter, encode_cursor
    from app.models.mentor import Mentor as MentorModel

    query = db.query(MentorModel)
    if university:
        query = query.filter(MentorModel.university.ilike(f"%{university}%"))
    if department:
        query = query.filter(MentorModel.department.ilike(f"%{department}%"))
    if research_direction:
        query = query.filter(MentorModel.research_directions.contains([research_direction]))
    if min_rating is not None:
        query = query.filter(MentorModel.avg_rating >= min_rating)
    if enrollment_status:
        query = query.filter(MentorModel.enrollment_status == enrollment_status)
    if search:
        query = query.filter(
            or_(
                MentorModel.name.ilike(f"%{search}%"),
                MentorModel.research_directions.contains([search]),
            )
        )
    query = apply_cursor_filter(
        query, cursor, time_col=MentorModel.created_at, id_col=MentorModel.id
    )
    items = (
        query.order_by(MentorModel.avg_rating.desc(), MentorModel.created_at.desc())
        .limit(page_size + 1)
        .all()
    )
    has_more = len(items) > page_size
    if has_more:
        items = items[:page_size]
    next_cursor = encode_cursor(items[-1].created_at, str(items[-1].id)) if has_more and items else None
    return CursorPaginatedResponse(
        items=[MentorResponse.model_validate(m) for m in items],
        next_cursor=next_cursor,
        has_more=has_more,
    )


@router.get("/kaoyan-mentors/{mentor_id}", response_model=MentorResponse, tags=["考研导师评价"])
def get_kaoyan_mentor(
    mentor_id: UUID,
    db: Session = Depends(get_db),
):
    """获取单个导师详情"""
    mentor = get_mentor(db, mentor_id)
    if not mentor:
        raise NotFoundError("导师不存在")
    return MentorResponse.model_validate(mentor)


@router.post("/kaoyan-mentors", response_model=MentorResponse, status_code=status.HTTP_201_CREATED, tags=["考研导师评价"])
def create_kaoyan_mentor(
    mentor_data: MentorCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建导师（需登录）"""
    mentor = create_mentor(db, mentor_data)
    return MentorResponse.model_validate(mentor)


@router.put("/kaoyan-mentors/{mentor_id}", response_model=MentorResponse, tags=["考研导师评价"])
def update_kaoyan_mentor(
    mentor_id: UUID,
    mentor_data: MentorUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """更新导师信息（需登录）"""
    mentor = update_mentor(db, mentor_id, mentor_data)
    if not mentor:
        raise NotFoundError("导师不存在")
    return MentorResponse.model_validate(mentor)


# === 导师评价 API ===

@router.get("/kaoyan-mentors/{mentor_id}/reviews", response_model=MentorReviewListResponse, tags=["考研导师评价"])
def list_mentor_reviews(
    mentor_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="审核状态筛选"),
    db: Session = Depends(get_db),
):
    """获取导师评价列表"""
    reviews, total = get_mentor_reviews(db, mentor_id, page, page_size, status)
    return MentorReviewListResponse(
        items=[MentorReviewResponse.model_validate(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/kaoyan-mentors/{mentor_id}/reviews", response_model=MentorReviewResponse, status_code=status.HTTP_201_CREATED, tags=["考研导师评价"])
def submit_mentor_review(
    mentor_id: UUID,
    review_data: MentorReviewCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交导师评价（需登录，防刷评）"""
    # 获取客户端 IP
    ip_address = request.client.host if request.client else None
    
    # 检查重复评价
    if check_duplicate_review(db, user.id, mentor_id, ip_address):
        raise BusinessError(
            "DUPLICATE_REVIEW",
            "您已评价过该导师，或同一 IP 30 天内已评价过",
            400,
        )

    # 创建评价
    review = create_mentor_review(db, mentor_id, user.id, review_data, ip_address)
    return MentorReviewResponse.model_validate(review)


@router.post("/kaoyan-reviews/{review_id}/like", tags=["考研导师评价"])
def like_mentor_review(
    review_id: UUID,
    db: Session = Depends(get_db),
):
    """点赞评价（无需登录）"""
    review = like_review(db, review_id)
    if not review:
        raise NotFoundError("评价不存在")
    return {"message": "点赞成功", "like_count": review.like_count}


@router.post("/kaoyan-reviews/{review_id}/approve", tags=["考研导师评价"])
def approve_mentor_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """审核通过评价（需管理员权限）"""
    if not user.is_admin:
        raise ForbiddenError("需要管理员权限")

    review = approve_review(db, review_id)
    if not review:
        raise NotFoundError("评价不存在")
    return {"message": "审核通过", "review_id": str(review.id)}


@router.post("/kaoyan-reviews/{review_id}/reject", tags=["考研导师评价"])
def reject_mentor_review(
    review_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """拒绝评价（需管理员权限）"""
    if not user.is_admin:
        raise ForbiddenError("需要管理员权限")

    review = reject_review(db, review_id)
    if not review:
        raise NotFoundError("评价不存在")
    return {"message": "已拒绝", "review_id": str(review.id)}


# === 批量查询接口 ===

@router.post("/batch", response_model=list[MentorResponse], tags=["考研导师评价"])
def batch_mentors(
    body: MentorBatchRequest,
    db: Session = Depends(get_db),
):
    """批量获取导师信息（消除前端 N+1 调用）。

    前端在院校列表/对比页一次展示 N 位导师时，原需发 N 次
    `/kaoyan-mentors/{id}` 请求；本接口一次返回所有导师详情。
    """
    from app.models.mentor import Mentor as MentorModel

    # 限制单次最多 100 个，防止滥用
    raw_ids = body.ids[:100]
    parsed_ids: list[UUID] = []
    for raw in raw_ids:
        try:
            parsed_ids.append(UUID(raw))
        except (ValueError, AttributeError):
            continue
    if not parsed_ids:
        return []
    items = db.query(MentorModel).filter(MentorModel.id.in_(parsed_ids)).all()
    return [MentorResponse.model_validate(m) for m in items]

