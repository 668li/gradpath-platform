"""失败案例库 API — 对冲幸存者偏差的真实失败叙事。

设计：
- 列表 / 详情 / 统计：公开访问，无需登录
- 分享案例 / 标记有帮助：需登录，但匿名存储（不写 user_id）
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.rate_limit import rate_limits
from app.database import get_db
from app.main import limiter
from app.models.user import User
from app.schemas.failure_case import (
    FailureCaseCreate,
    FailureCaseListResponse,
    FailureCaseResponse,
    FailureCaseStatsResponse,
)
from app.services.failure_case_service import (
    create_case,
    get_case,
    get_stats,
    increment_view,
    list_approved_cases,
    mark_helpful,
)

router = APIRouter(prefix="/api/failure-cases", tags=["失败案例库"])


@router.get("", response_model=FailureCaseListResponse)
def list_cases(
    path_type: str | None = Query(None, description="路径筛选：kaoyan/civil_service/employment/study_abroad"),
    stage: str | None = Query(None, description="阶段筛选：preparation/interview/final_year1/year2_plus"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=50, description="每页数量"),
    db: Session = Depends(get_db),
):
    """获取已审核失败案例列表（公开访问，无需登录）。"""
    return list_approved_cases(db, path_type=path_type, stage=stage, page=page, size=size)


@router.get("/stats", response_model=FailureCaseStatsResponse)
def get_stats_endpoint(
    db: Session = Depends(get_db),
):
    """获取失败案例统计数据（按路径/阶段分布）。"""
    return get_stats(db)


@router.get("/{case_id}", response_model=FailureCaseResponse)
def get_case_endpoint(
    case_id: UUID,
    db: Session = Depends(get_db),
):
    """获取失败案例详情（自动增加浏览数）。"""
    case = get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    if case.status != "approved":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    increment_view(db, case_id)
    db.refresh(case)
    return FailureCaseResponse.model_validate(case)


@router.post(
    "",
    response_model=FailureCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit(rate_limits.EXPERIENCE_POST_CREATE)
def create_case_endpoint(
    request: Request,
    response: Response,
    data: FailureCaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """分享失败案例（需登录，但匿名存储 — 不写 user_id）。"""
    # user 仅做身份校验，不写入案例；保留 user 引用避免 lint 警告
    _ = user
    case = create_case(db, data)
    # 创建后 status=pending，对外只返回基本字段
    return FailureCaseResponse.model_validate(case)


@router.post("/{case_id}/helpful")
def mark_helpful_endpoint(
    case_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """标记案例有帮助（需登录）。"""
    _ = user
    case = mark_helpful(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="案例不存在")
    return {"message": "感谢反馈", "helpful_count": case.helpful_count}
