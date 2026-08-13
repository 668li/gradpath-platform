"""7天微行动 API — 7 天低成本探索任务。

端点：
- POST /api/micro-actions/plans              — 创建 7 天微行动计划
- GET  /api/micro-actions/plans/current      — 获取当前活跃 plan
- GET  /api/micro-actions/plans/{plan_id}    — 获取指定 plan
- POST /api/micro-actions/tasks/{task_id}/complete — 完成任务（带记录）
- POST /api/micro-actions/tasks/{task_id}/skip     — 跳过任务
- GET  /api/micro-actions/history            — 获取历史 plan 列表
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.micro_action import MicroActionPlan, MicroActionTask
from app.models.user import User
from app.schemas.micro_action import (
    MicroActionPlanCreate,
    MicroActionPlanResponse,
    MicroActionTaskResponse,
    TaskCompleteRequest,
)
from app.services import micro_action_service as svc

router = APIRouter(prefix="/api/micro-actions", tags=["7天微行动"])


def _to_plan_response(plan: MicroActionPlan, tasks: list[MicroActionTask]) -> MicroActionPlanResponse:
    """构造 plan 响应（含任务列表与进度）。"""
    progress = svc._calculate_progress(tasks)
    return MicroActionPlanResponse(
        id=plan.id,
        target_path=plan.target_path,
        target_role=plan.target_role,
        status=plan.status,
        started_at=plan.started_at,
        completed_at=plan.completed_at,
        tasks=[MicroActionTaskResponse.model_validate(t) for t in tasks],
        progress=progress,
        self_discovery_report=plan.self_discovery_report,
    )


def _load_plan_with_tasks(db: Session, plan: MicroActionPlan) -> MicroActionPlanResponse:
    tasks = (
        db.query(MicroActionTask)
        .filter(MicroActionTask.plan_id == plan.id)
        .order_by(MicroActionTask.day_number)
        .all()
    )
    return _to_plan_response(plan, tasks)


@router.post("/plans", response_model=MicroActionPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    req: MicroActionPlanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MicroActionPlanResponse:
    """创建 7 天微行动计划，自动生成 7 个任务。"""
    plan = svc.create_plan(db, user.id, req.target_path, req.target_role)
    return _load_plan_with_tasks(db, plan)


@router.get("/plans/current", response_model=MicroActionPlanResponse | None)
def get_current_plan(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MicroActionPlanResponse | None:
    """获取当前活跃 plan，没有时返回 null。"""
    plan = svc.get_current_plan(db, user.id)
    if plan is None:
        return None
    return _load_plan_with_tasks(db, plan)


@router.get("/plans/{plan_id}", response_model=MicroActionPlanResponse)
def get_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MicroActionPlanResponse:
    """获取指定 plan（必须属于当前用户）。"""
    plan = svc.get_plan(db, _parse_uuid(plan_id))
    if plan is None or plan.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计划不存在")
    return _load_plan_with_tasks(db, plan)


@router.post("/tasks/{task_id}/complete", response_model=MicroActionTaskResponse)
async def complete_task(
    task_id: str,
    req: TaskCompleteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MicroActionTaskResponse:
    """完成任务：标记完成 + 生成 AI 洞察 + 检查 plan 完成状态。"""
    task = svc.get_task(db, _parse_uuid(task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    # 校验任务归属
    plan = svc.get_plan(db, task.plan_id)
    if plan is None or plan.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    updated = await svc.complete_task(db, task.id, req.user_response)
    return MicroActionTaskResponse.model_validate(updated)


@router.post("/tasks/{task_id}/skip", response_model=MicroActionTaskResponse)
def skip_task(
    task_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MicroActionTaskResponse:
    """跳过任务：仅标记状态。"""
    task = svc.get_task(db, _parse_uuid(task_id))
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")
    plan = svc.get_plan(db, task.plan_id)
    if plan is None or plan.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    updated = svc.skip_task(db, task.id)
    return MicroActionTaskResponse.model_validate(updated)


@router.get("/history", response_model=list[MicroActionPlanResponse])
def get_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[MicroActionPlanResponse]:
    """获取用户所有 plan 历史。"""
    plans = svc.get_history(db, user.id)
    return [_load_plan_with_tasks(db, p) for p in plans]


def _parse_uuid(value: str):
    """把字符串解析为 UUID，非法时抛 400。"""
    from uuid import UUID

    try:
        return UUID(value)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="无效的 ID 格式"
        )
