"""考公作战室 API 路由。"""
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.civil_service_intel import (
    CivilServiceDarkKnowledgeResponse,
    CivilServicePositioningCreateRequest,
    CivilServicePositioningResponse,
    DarkKnowledgeStageInfo,
    PostIntelQueryRequest,
    PostIntelResponse,
    PostIntelSaveRequest,
)
from app.services.civil_service_intel_service import (
    create_civil_service_positioning,
    delete_post_intel,
    get_civil_service_dark_knowledge_by_stage,
    get_civil_service_dark_knowledge_stages,
    get_civil_service_positioning_history,
    get_latest_civil_service_positioning,
    get_user_post_intel_list,
    query_post_intel,
    save_post_intel,
    seed_civil_service_dark_knowledge,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/civil-service", tags=["考公作战室"])


def _ensure_seeded(db: Session) -> None:
    stages = get_civil_service_dark_knowledge_stages(db)
    total = sum(s["count"] for s in stages)
    if total == 0:
        seed_civil_service_dark_knowledge(db)


# ============ 岗位情报 ============

@router.post("/post-intel/query", response_model=dict[str, Any])
async def query_post_intel_endpoint(payload: PostIntelQueryRequest) -> Any:
    """AI 生成岗位情报画像。"""
    try:
        result = await query_post_intel(
            region=payload.region,
            department=payload.department,
            post_name=payload.post_name,
            exam_type=payload.exam_type or "",
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.exception("AI 生成岗位情报失败: %s", e)
        raise HTTPException(status_code=500, detail="AI 生成岗位情报失败，请稍后重试") from e


@router.post("/post-intel", response_model=PostIntelResponse)
def save_post_intel_endpoint(
    payload: PostIntelSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    """保存岗位情报到我的档案。"""
    intel = save_post_intel(db, user.id, payload.model_dump())
    return intel


@router.get("/post-intel", response_model=list[PostIntelResponse])
def list_post_intel_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    """获取我已保存的岗位情报列表。"""
    return get_user_post_intel_list(db, user.id)


@router.get("/post-intel/public", response_model=list[PostIntelResponse])
def list_public_post_intel_endpoint(
    region: str | None = None,
    department: str | None = None,
    exam_type: str | None = None,
    department_tier: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> Any:
    """公开浏览所有岗位情报（无需登录）。"""
    from app.models.civil_service_intel import PostIntel
    query = db.query(PostIntel)
    if region:
        query = query.filter(PostIntel.region.ilike(f"%{region}%"))
    if department:
        query = query.filter(PostIntel.department.ilike(f"%{department}%"))
    if exam_type:
        query = query.filter(PostIntel.exam_type == exam_type)
    if department_tier:
        query = query.filter(PostIntel.department_tier == department_tier)
    items = query.order_by(
        PostIntel.department_tier,
        PostIntel.region,
        PostIntel.department,
    ).limit(limit).all()
    return items


@router.delete("/post-intel/{intel_id}")
def delete_post_intel_endpoint(
    intel_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    """删除岗位情报。"""
    success = delete_post_intel(db, user.id, intel_id)
    if not success:
        raise HTTPException(status_code=404, detail="情报不存在或无权删除")
    return {"success": True}


# ============ 考公定位 ============

@router.post("/positioning", response_model=CivilServicePositioningResponse)
async def create_positioning_endpoint(
    payload: CivilServicePositioningCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    """创建考公定位评估（触发 AI 分析）。"""
    # 修复 bug: 原先直接传 Pydantic 对象，service 层用 **data 解包失败
    # TypeError: CivilServicePositioning() argument after ** must be a mapping, not CivilServicePositioningCreateRequest
    positioning = await create_civil_service_positioning(db, user.id, payload.model_dump())
    return positioning


@router.get("/positioning/latest", response_model=CivilServicePositioningResponse | None)
def get_latest_positioning_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    """获取最新一次考公定位。"""
    return get_latest_civil_service_positioning(db, user.id)


@router.get("/positioning/history", response_model=list[CivilServicePositioningResponse])
def get_positioning_history_endpoint(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Any:
    """获取考公定位历史记录。"""
    return get_civil_service_positioning_history(db, user.id)


# ============ 考公暗知识 ============

@router.post("/dark-knowledge/seed")
def seed_dark_knowledge_endpoint(db: Session = Depends(get_db)) -> Any:
    """（初始化用）填充考公暗知识种子数据。"""
    count = seed_civil_service_dark_knowledge(db)
    return {"success": True, "count": count}


@router.get("/dark-knowledge/stages", response_model=list[DarkKnowledgeStageInfo])
def get_dark_knowledge_stages_endpoint(db: Session = Depends(get_db)) -> Any:
    """获取暗知识阶段列表（含各阶段数量）。"""
    _ensure_seeded(db)
    return get_civil_service_dark_knowledge_stages(db)


@router.get("/dark-knowledge", response_model=list[CivilServiceDarkKnowledgeResponse])
def get_dark_knowledge_endpoint(
    stage: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """按阶段获取考公暗知识。stage 为空则返回全部。"""
    _ensure_seeded(db)
    return get_civil_service_dark_knowledge_by_stage(db, stage)
