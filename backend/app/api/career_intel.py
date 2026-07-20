"""求职作战室 API — 公司情报 + 求职定位 + 求职暗知识。"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.career_intel import (
    CareerDarkKnowledgeResponse,
    CareerPositioningCreateRequest,
    CareerPositioningResponse,
    CompanyIntelQueryRequest,
    CompanyIntelResponse,
    CompanyIntelSaveRequest,
    DarkKnowledgeStageInfo,
)
from app.services import career_intel_service

router = APIRouter(prefix="/api/career-intel", tags=["求职作战室"])


# ===== 公司情报 =====

@router.post("/intel/query")
async def query_company_intel(
    body: CompanyIntelQueryRequest,
    user: User = Depends(get_current_user),
):
    """AI 查询公司情报（不保存，返回预览）。"""
    return await career_intel_service.query_company_intel(body.company_name, body.position_name)


@router.post("/intel/save", response_model=CompanyIntelResponse, status_code=status.HTTP_201_CREATED)
def save_company_intel(
    body: CompanyIntelSaveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """保存公司情报。"""
    data = body.model_dump()
    intel = career_intel_service.save_company_intel(db, user.id, data)
    return CompanyIntelResponse.model_validate(intel)


@router.get("/intel/list", response_model=list[CompanyIntelResponse])
def list_company_intel(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户保存的公司情报列表。"""
    items = career_intel_service.get_user_company_intel_list(db, user.id)
    return [CompanyIntelResponse.model_validate(i) for i in items]


@router.delete("/intel/{intel_id}")
def delete_company_intel(
    intel_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除公司情报。"""
    ok = career_intel_service.delete_company_intel(db, user.id, intel_id)
    if not ok:
        raise HTTPException(status_code=404, detail="情报不存在")
    return {"ok": True}


# ===== 求职定位 =====

@router.post("/positioning/create", response_model=CareerPositioningResponse, status_code=status.HTTP_201_CREATED)
async def create_positioning(
    body: CareerPositioningCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """创建求职定位（自动触发 AI 评估）。"""
    data = body.model_dump()
    positioning = await career_intel_service.create_career_positioning(db, user.id, data)
    return CareerPositioningResponse.model_validate(positioning)


@router.get("/positioning/latest", response_model=CareerPositioningResponse | None)
def get_latest_positioning(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取最新的求职定位。"""
    p = career_intel_service.get_latest_career_positioning(db, user.id)
    return CareerPositioningResponse.model_validate(p) if p else None


@router.get("/positioning/history", response_model=list[CareerPositioningResponse])
def get_positioning_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取求职定位历史。"""
    items = career_intel_service.get_career_positioning_history(db, user.id)
    return [CareerPositioningResponse.model_validate(i) for i in items]


# ===== 求职暗知识 =====

@router.get("/dark-knowledge/list", response_model=list[CareerDarkKnowledgeResponse])
def get_dark_knowledge(
    stage: str | None = Query(default=None),
    page: int = 1,
    per_page: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取求职暗知识列表（按阶段过滤，支持分页）。"""
    items, _total = career_intel_service.get_career_dark_knowledge_by_stage(db, stage, page=page, limit=per_page)
    return [CareerDarkKnowledgeResponse.model_validate(i) for i in items]


@router.get("/dark-knowledge/stages", response_model=list[DarkKnowledgeStageInfo])
def get_dark_knowledge_stages(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取求职暗知识各阶段统计。"""
    career_intel_service.seed_career_dark_knowledge(db)
    return career_intel_service.get_career_dark_knowledge_stages(db)


@router.post("/dark-knowledge/seed")
def seed_dark_knowledge(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """手动触发求职暗知识播种。"""
    count = career_intel_service.seed_career_dark_knowledge(db)
    return {"seeded": count}
