"""考研情报 API — 院校情报、暗知识、研招网数据。"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.core.deps import get_current_user
from app.database import get_db
from app.models.grad_intel import GradSchoolIntel
from app.models.user import User
from app.schemas.grad_intel import (
    DarkKnowledgeResponse,
    GradYanzhaoProgramResponse,
    IntelResponse,
    IntelSaveRequest,
    PaginatedDarkKnowledgeResponse,
)
from app.services import grad_intel_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/grad-intel", tags=["考研情报"])


# ===== 院校情报 =====


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

    items, total = grad_intel_service.get_dark_knowledge_by_stage(
        db, stage, page=page, limit=per_page
    )
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
    items = (
        query.order_by(
            GradSchoolIntel.school_tier,
            GradSchoolIntel.school_name,
            GradSchoolIntel.major_name,
        )
        .limit(limit)
        .all()
    )
    return [IntelResponse.model_validate(i) for i in items]


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
    if isinstance(cached_result, list):
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

    # 必须缓存 dict 列表：ORM 对象经 json.dumps(default=str) 会存成垃圾字符串，
    # Redis 命中即 500（09-05 对抗审查实证，/scorelines 的手转 dict 是正确范式）
    cache.set(
        cache_key,
        [GradYanzhaoProgramResponse.model_validate(item).model_dump(mode="json") for item in items],
        ttl=600,
    )
    response.headers["Cache-Control"] = "public, max-age=600"
    return items


class SchoolAnnouncementResponse(BaseModel):
    """院校官方公告条目（归口自已审核研招公告）。"""

    id: str
    title: str
    summary: str | None = None
    source_url: str
    source_platform: str
    published_at: str | None = None
    category: str
    quality_grade: str | None = None


@router.get(
    "/schools/{university_name}/announcements",
    response_model=list[SchoolAnnouncementResponse],
)
def get_school_announcements(
    university_name: str,
    limit: int = Query(20, ge=1, le=50, description="返回条数"),
    db: Session = Depends(get_db),
):
    """获取归口到某院校的已审核官方公告（公开接口，5分钟缓存）。

    归口规则见 grad_intel_service.get_school_announcements：
    域名后缀匹配，跳过校区歧义/第三方聚合/公众号，只取 approved。
    """
    cache_key = f"school_announcements:{university_name}:{limit}"
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return cached_result
    result = grad_intel_service.get_school_announcements(db, university_name, limit=limit)
    cache.set(cache_key, result, ttl=300)
    return result
