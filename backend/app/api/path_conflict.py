"""路径冲突调解 API — 当测评结果与用户现状冲突时提供 3 条路径让用户自主选择。

端点：
- POST /api/path-conflict/detect  — 检测冲突，返回冲突摘要 + 3 条选项 + conflict_id
- POST /api/path-conflict/resolve — 提交用户选择（基于 conflict_id）
- GET  /api/path-conflict/history — 获取历史调解记录
- GET  /api/path-conflict/{id}    — 获取单条调解详情
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.path_conflict import PathConflictResolution
from app.models.user import User
from app.schemas.path_conflict import (
    PathConflictDetectResponse,
    PathConflictResolutionResponse,
    PathConflictResolveRequest,
)
from app.services import path_conflict_service as svc

router = APIRouter(prefix="/api/path-conflict", tags=["路径冲突调解"])


@router.post("/detect", response_model=PathConflictDetectResponse)
def detect_conflict(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """检测用户的测评结果与当前现状是否冲突。

    - 若存在冲突：生成 3 条路径选项，并创建一条 pending 记录（selected_option=None），
      返回 conflict_id 供后续 /resolve 使用。
    - 若无冲突：返回 has_conflict=False 与提示信息，不创建记录。
    """
    result = svc.detect_conflict(db, user.id)

    if not result.get("has_conflict"):
        return PathConflictDetectResponse(
            conflict_id="",
            conflict_type=result.get("conflict_type", "no_conflict"),
            has_conflict=False,
            assessment_summary=result.get("assessment_summary", {}),
            current_situation=result.get("current_situation", {}),
            options=[],
            message=result.get("message", "暂无冲突"),
        )

    # 有冲突：生成选项 + 创建 pending 记录
    options = svc.generate_options(result["assessment_summary"], result["current_situation"])

    # 创建 pending 记录，返回 conflict_id
    pending = PathConflictResolution(
        user_id=user.id,
        conflict_type=result["conflict_type"],
        assessment_summary=result["assessment_summary"],
        current_situation=result["current_situation"],
        options=options,
        selected_option=None,
        reasoning="",
        action_plan={},
    )
    db.add(pending)
    db.commit()
    db.refresh(pending)

    return PathConflictDetectResponse(
        conflict_id=str(pending.id),
        conflict_type=result["conflict_type"],
        has_conflict=True,
        assessment_summary=result["assessment_summary"],
        current_situation=result["current_situation"],
        options=options,
        message=result.get("message", ""),
    )


@router.post("/resolve", response_model=PathConflictResolutionResponse)
def resolve_conflict(
    body: PathConflictResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交用户对冲突的选择，生成并返回行动计划。"""
    try:
        conflict_id = UUID(body.conflict_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的 conflict_id",
        )

    record = (
        db.query(PathConflictResolution)
        .filter(
            PathConflictResolution.id == conflict_id,
            PathConflictResolution.user_id == user.id,
        )
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="冲突记录不存在，请先调用 /detect",
        )

    # 更新选择与理由
    record.selected_option = body.selected_option
    record.reasoning = body.reasoning or ""

    # 生成行动计划
    action_plan = svc.generate_action_plan(record)
    record.action_plan = action_plan

    db.commit()
    db.refresh(record)
    return PathConflictResolutionResponse.model_validate(record)


@router.get("/history", response_model=list[PathConflictResolutionResponse])
def list_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户的历史调解记录（按时间倒序）。"""
    records = svc.list_resolutions(db, user.id)
    return [PathConflictResolutionResponse.model_validate(r) for r in records]


@router.get("/{resolution_id}", response_model=PathConflictResolutionResponse)
def get_resolution(
    resolution_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单条调解记录详情。"""
    record = svc.get_resolution(db, user.id, resolution_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="调解记录不存在",
        )
    return PathConflictResolutionResponse.model_validate(record)
