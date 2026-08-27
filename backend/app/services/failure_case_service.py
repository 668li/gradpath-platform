"""失败案例库服务层 — 匿名分享、列表筛选、统计、互动。"""

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.failure_case import FailureCase
from app.schemas.failure_case import (
    PATH_TYPES,
    STAGES,
    FailureCaseCreate,
    FailureCaseListResponse,
    FailureCaseResponse,
    FailureCaseStatsResponse,
)

logger = logging.getLogger(__name__)


def _atomic_increment(db: Session, item_id: UUID, column: str, delta: int = 1) -> bool:
    """原子 UPDATE — 避免 read-modify-write 在高并发下丢失更新。"""
    col = getattr(FailureCase, column)
    rows = db.query(FailureCase).filter(FailureCase.id == item_id).update({col: col + delta})
    return rows > 0


def _validate_path_and_stage(path_type: str, stage: str) -> None:
    """校验路径与阶段是否在白名单内。"""
    if path_type not in PATH_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的 path_type: {path_type}，可选: {sorted(PATH_TYPES)}",
        )
    if stage not in STAGES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"无效的 stage: {stage}，可选: {sorted(STAGES)}",
        )


def create_case(db: Session, data: FailureCaseCreate) -> FailureCase:
    """创建失败案例（默认 status=pending，待审核）。"""
    _validate_path_and_stage(data.path_type, data.stage)

    case = FailureCase(
        author_role=data.author_role.strip(),
        path_type=data.path_type,
        stage=data.stage,
        title=data.title.strip(),
        story=data.story.strip(),
        lessons=data.lessons or [],
        regrets=data.regrets or [],
        what_would_i_do=data.what_would_i_do.strip(),
        status="pending",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    logger.info("创建失败案例 id=%s path=%s stage=%s", case.id, case.path_type, case.stage)
    return case


def get_case(db: Session, case_id: UUID) -> FailureCase | None:
    """获取单个失败案例。"""
    return db.query(FailureCase).filter(FailureCase.id == case_id).first()


def list_approved_cases(
    db: Session,
    path_type: str | None = None,
    stage: str | None = None,
    page: int = 1,
    size: int = 10,
) -> FailureCaseListResponse:
    """分页查询已审核案例。

    - 只返回 status=approved 的案例
    - 支持按 path_type / stage 筛选
    - 按创建时间倒序
    """
    query = db.query(FailureCase).filter(FailureCase.status == "approved")

    if path_type:
        _validate_path_and_stage(path_type, "preparation")  # 仅校验 path_type
        query = query.filter(FailureCase.path_type == path_type)
    if stage:
        _validate_path_and_stage("kaoyan", stage)  # 仅校验 stage
        query = query.filter(FailureCase.stage == stage)

    total = query.count()
    offset = (page - 1) * size
    items = query.order_by(FailureCase.created_at.desc()).offset(offset).limit(size).all()

    return FailureCaseListResponse(
        items=[FailureCaseResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=size,
    )


def mark_helpful(db: Session, case_id: UUID) -> FailureCase | None:
    """标记案例有帮助（helpful_count + 1）。"""
    case = get_case(db, case_id)
    if not case:
        return None
    _atomic_increment(db, case_id, "helpful_count", 1)
    db.commit()
    db.refresh(case)
    return case


def increment_view(db: Session, case_id: UUID) -> bool:
    """增加浏览数（view_count + 1）。"""
    ok = _atomic_increment(db, case_id, "view_count", 1)
    if ok:
        db.commit()
    return ok


def get_stats(db: Session) -> FailureCaseStatsResponse:
    """统计数据：总案例数 + 按路径/阶段分布（仅 approved）。"""
    base_q = db.query(FailureCase).filter(FailureCase.status == "approved")
    total = base_q.count()

    by_path_rows = (
        db.query(FailureCase.path_type, func.count(FailureCase.id))
        .filter(FailureCase.status == "approved")
        .group_by(FailureCase.path_type)
        .all()
    )
    by_stage_rows = (
        db.query(FailureCase.stage, func.count(FailureCase.id))
        .filter(FailureCase.status == "approved")
        .group_by(FailureCase.stage)
        .all()
    )

    return FailureCaseStatsResponse(
        total=total,
        by_path={(p or "unknown"): c for p, c in by_path_rows},
        by_stage={(s or "unknown"): c for s, c in by_stage_rows},
    )
