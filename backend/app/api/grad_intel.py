"""考研情报 API — 院校情报、自我定位、暗知识。"""
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.grad_intel import GradSchoolIntel
from app.models.user import User
from app.schemas.grad_intel import (
    DarkKnowledgeResponse,
    GradAdjustmentInfoResponse,
    GradScorelineRecordResponse,
    GradScorelineTrendResponse,
    GradSchoolDataSummaryResponse,
    GradYanzhaoProgramResponse,
    IntelQueryRequest,
    IntelResponse,
    IntelSaveRequest,
    PaginatedDarkKnowledgeResponse,
    PositioningCreateRequest,
    PositioningResponse,
)
from app.schemas.mentor import (
    MentorListResponse,
    MentorResponse,
    MentorReviewListResponse,
    MentorReviewResponse,
)
from app.services import grad_intel_service
from app.services import mentor_service
from app.core.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/grad-intel", tags=["考研情报"])


# ===== 院校情报 =====

@router.post("/intel/query")
async def query_intel(
    body: IntelQueryRequest,
    user: User = Depends(get_current_user),
):
    """AI 生成院校情报。不保存，返回结构化结果供前端展示。"""
    try:
        result = await grad_intel_service.query_school_intel(body.school_name, body.major_name)
        return result
    except Exception as e:
        logger.exception("AI 情报生成失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 情报生成失败，请稍后重试",
        )


@router.post("/intel/save", response_model=IntelResponse)
def save_intel(
    body: IntelSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存院校情报。"""
    # 修复 bug: 重复保存触发 UNIQUE constraint -> 500，应转 409 Conflict
    try:
        intel = grad_intel_service.save_intel(db, user.id, body.model_dump())
    except Exception as e:
        from sqlalchemy.exc import IntegrityError
        if isinstance(e, IntegrityError):
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="该院校+专业情报已存在，请勿重复保存",
            )
        logger.exception("保存院校情报失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存情报失败，请稍后重试",
        )
    return IntelResponse.model_validate(intel)


@router.get("/intel/list", response_model=list[IntelResponse])
def list_intel(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户保存的院校情报列表。"""
    items = grad_intel_service.get_user_intel_list(db, user.id)
    return [IntelResponse.model_validate(i) for i in items]


@router.delete("/intel/{intel_id}")
def delete_intel(
    intel_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除院校情报。"""
    ok = grad_intel_service.delete_intel(db, user.id, intel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="情报不存在")
    return {"ok": True}


# ===== 自我定位 =====

@router.post("/positioning/create", response_model=PositioningResponse)
async def create_positioning(
    body: PositioningCreateRequest,
    bypass_cache: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建自我定位并触发 AI 评估。

    Args:
        bypass_cache: 是否绕过缓存强制重新生成
    """
    try:
        positioning = await grad_intel_service.create_positioning(
            db, user.id, body.model_dump(), bypass_cache=bypass_cache
        )
        return PositioningResponse.model_validate(positioning)
    except Exception as e:
        # 修复: FASTAPI-RESP-001 — 不向客户端泄漏内部异常信息，仅记录日志
        logger.exception("create_positioning failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI 评估服务暂时不可用，请稍后重试",
        )


@router.post("/positioning/clear-cache")
def clear_positioning_cache(
    user: User = Depends(get_current_user),
):
    """清除用户的 AI 结果缓存。"""
    # 修复 bug: 原先调用 grad_intel_service._ai_cache.clear() 触发 AttributeError → 500
    # _ai_cache 属性从未定义（旧实现已重构为 cache 模块）
    deleted = grad_intel_service.clear_positioning_cache()
    return {"message": "缓存已清除", "cleared_count": deleted}


@router.get("/positioning/latest", response_model=PositioningResponse | None)
def get_latest_positioning(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取最新的自我定位。"""
    p = grad_intel_service.get_latest_positioning(db, user.id)
    return PositioningResponse.model_validate(p) if p else None


@router.get("/positioning/history", response_model=list[PositioningResponse])
def get_positioning_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取自我定位历史。"""
    items = grad_intel_service.get_positioning_history(db, user.id)
    return [PositioningResponse.model_validate(i) for i in items]


# ===== 暗知识 =====

@router.get("/dark-knowledge/list", response_model=PaginatedDarkKnowledgeResponse)
def list_dark_knowledge(
    response: Response,
    stage: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取暗知识列表，可按阶段过滤（公开接口）。"""
    cache_key = f"dark_knowledge_list:{stage}:{page}:{per_page}"
    cached = cache.get(cache_key)
    if cached is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
        return cached

    items, total = grad_intel_service.get_dark_knowledge_by_stage(db, stage, page=page, limit=per_page)
    pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    resp = PaginatedDarkKnowledgeResponse(
        items=[DarkKnowledgeResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=per_page,
        pages=pages,
    )
    cache.set(cache_key, resp.model_dump(), ttl=300)
    response.headers["Cache-Control"] = "public, max-age=300"
    return resp


@router.get("/dark-knowledge/stages")
def get_dark_knowledge_stages(
    db: Session = Depends(get_db),
):
    """获取暗知识阶段列表（公开接口）。"""
    return grad_intel_service.get_dark_knowledge_stages(db)


# ===== 公开浏览接口（无需登录）=====

@router.get("/intel/public", response_model=list[IntelResponse])
def list_public_intel(
    school_name: str | None = None,
    major_name: str | None = None,
    school_tier: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """公开浏览所有院校情报（无需登录）。"""
    query = db.query(GradSchoolIntel)
    if school_name:
        query = query.filter(GradSchoolIntel.school_name.ilike(f"%{school_name}%"))
    if major_name:
        query = query.filter(GradSchoolIntel.major_name.ilike(f"%{major_name}%"))
    if school_tier:
        query = query.filter(GradSchoolIntel.school_tier == school_tier)
    items = query.order_by(
        GradSchoolIntel.school_tier,
        GradSchoolIntel.school_name,
        GradSchoolIntel.major_name,
    ).limit(limit).all()
    return [IntelResponse.model_validate(i) for i in items]


@router.post("/dark-knowledge/seed")
def seed_dark_knowledge(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动触发暗知识预填充（开发用）。"""
    count = grad_intel_service.seed_dark_knowledge(db)
    return {"seeded": count, "total": db.query(grad_intel_service.DarkKnowledge).count()}


# ===== 研招网真实数据（公开浏览） =====

@router.get("/yanzhao-programs", response_model=list[GradYanzhaoProgramResponse])
def list_yanzhao_programs(
    response: Response,
    university_name: str | None = None,
    major_name: str | None = None,
    department: str | None = None,
    degree_type: str | None = None,
    year: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """查询研招网真实专业目录（公开接口，10分钟缓存）。"""
    cache_key = f"yanzhao_programs:{university_name}:{major_name}:{department}:{degree_type}:{year}:{limit}:{offset}"

    cached_result = cache.get(cache_key)
    if cached_result is not None:
        response.headers["Cache-Control"] = "public, max-age=600"
        return cached_result

    result = grad_intel_service.list_yanzhao_programs(
        db,
        university_name=university_name,
        major_name=major_name,
        department=department,
        degree_type=degree_type,
        year=year,
        limit=limit,
        offset=offset,
    )
    
    items = result[0] if isinstance(result, tuple) else result

    cache.set(cache_key, items, ttl=600)
    response.headers["Cache-Control"] = "public, max-age=600"
    return items


@router.get("/scorelines")
def list_scorelines(
    university_name: str | None = None,
    major_name: str | None = None,
    degree_type: str | None = None,
    year: int | None = None,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """查询真实复试分数线（公开接口，5分钟缓存）。"""
    cache_key = f"scorelines:{university_name}:{major_name}:{degree_type}:{year}:{limit}:{offset}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    
    items = grad_intel_service.list_scoreline_records(
        db, university_name=university_name, major_name=major_name,
        degree_type=degree_type, year=year, limit=limit, offset=offset,
    )
    # 在session关闭前转换为字典
    result = [
        {
            "id": str(item.id),
            "university_name": item.university_name,
            "major_name": item.major_name,
            "degree_type": item.degree_type,
            "year": item.year,
            "total_score_line": item.total_score_line,
            "politics_score": item.politics_score,
            "foreign_language_score": item.foreign_language_score,
            "business_1_score": item.business_1_score,
            "business_2_score": item.business_2_score,
            "enrollment_count": item.enrollment_count,
            "application_count": item.application_count,
            "adjustment_count": item.adjustment_count,
            "data_sources": item.data_sources or [],
        }
        for item in items
    ]
    cache.set(cache_key, result, ttl=300)
    return result


@router.get("/scorelines/trend", response_model=GradScorelineTrendResponse)
def get_scoreline_trend(
    university_name: str,
    major_name: str,
    degree_type: str | None = None,
    db: Session = Depends(get_db),
):
    """获取某院校某专业的复试分数线趋势（公开接口，5分钟缓存）。"""
    # 生成缓存键
    cache_key = f"scoreline_trend:{university_name}:{major_name}:{degree_type}"

    # 尝试从缓存获取
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    # 查询数据库
    result = grad_intel_service.get_scoreline_trend(
        db, university_name=university_name, major_name=major_name, degree_type=degree_type
    )

    # 缓存结果（5分钟）
    cache.set(cache_key, result, ttl=300)
    return result


@router.get("/adjustments", response_model=list[GradAdjustmentInfoResponse])
def list_adjustments(
    university_name: str | None = None,
    major_name: str | None = None,
    status: str | None = None,
    year: int | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """查询调剂信息（公开接口，5分钟缓存）。"""
    cache_key = f"adjustments:{university_name}:{major_name}:{status}:{year}:{limit}:{offset}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    result = grad_intel_service.list_adjustment_info(
        db,
        university_name=university_name,
        major_name=major_name,
        status=status,
        year=year,
        limit=limit,
        offset=offset,
    )
    cache.set(cache_key, result, ttl=300)
    return result


@router.get("/schools/{university_name}/summary", response_model=GradSchoolDataSummaryResponse)
def get_school_summary(
    university_name: str,
    db: Session = Depends(get_db),
):
    """获取某院校的数据汇总（公开接口，5分钟缓存）。"""
    cache_key = f"school_summary:{university_name}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    result = grad_intel_service.get_school_data_summary(db, university_name)
    cache.set(cache_key, result, ttl=300)
    return result


class SchoolBatchRequest(BaseModel):
    """批量获取院校数据汇总请求体。"""
    university_names: list[str] = Field(
        ..., min_length=1, max_length=100, description="院校名称列表（最多 100 个）"
    )


@router.post("/schools/batch", response_model=list[GradSchoolDataSummaryResponse])
def batch_school_summaries(
    body: SchoolBatchRequest,
    db: Session = Depends(get_db),
):
    """批量获取多所院校的数据汇总（消除前端 N+1 调用，5分钟缓存）。

    前端在院校列表页一次加载 N 所院校时，原需发 N 次
    `/schools/{name}/summary` 请求；本接口一次返回所有院校的汇总。
    """
    # 限制单次最多 100 所，防止滥用
    names = body.university_names[:100]
    results: list[GradSchoolDataSummaryResponse] = []
    for name in names:
        cache_key = f"school_summary:{name}"
        cached = cache.get(cache_key)
        if cached is not None:
            results.append(GradSchoolDataSummaryResponse(**cached))
            continue
        summary = grad_intel_service.get_school_data_summary(db, name)
        cache.set(cache_key, summary, ttl=300)
        results.append(GradSchoolDataSummaryResponse(**summary))
    return results


# ===== 导师评价 =====

@router.get("/mentors", response_model=MentorListResponse)
def list_mentors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    university: str | None = None,
    department: str | None = None,
    research_direction: str | None = None,
    min_rating: float | None = None,
    enrollment_status: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
):
    """获取导师列表，支持多维度筛选（公开接口）。"""
    mentors, total = mentor_service.get_mentors(
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


@router.get("/mentors/{mentor_id}", response_model=MentorResponse)
def get_mentor_detail(
    mentor_id: UUID,
    db: Session = Depends(get_db),
):
    """获取导师详情（公开接口）。"""
    mentor = mentor_service.get_mentor(db, mentor_id)
    if not mentor:
        raise HTTPException(status_code=404, detail="导师不存在")
    return MentorResponse.model_validate(mentor)


@router.get("/mentors/{mentor_id}/reviews", response_model=MentorReviewListResponse)
def list_mentor_reviews(
    mentor_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: Session = Depends(get_db),
):
    """获取导师评价列表（公开接口）。"""
    mentor = mentor_service.get_mentor(db, mentor_id)
    if not mentor:
        raise HTTPException(status_code=404, detail="导师不存在")
    reviews, total = mentor_service.get_mentor_reviews(db, mentor_id, page, page_size, status)
    return MentorReviewListResponse(
        items=[MentorReviewResponse.model_validate(r) for r in reviews],
        total=total,
        page=page,
        page_size=page_size,
    )
