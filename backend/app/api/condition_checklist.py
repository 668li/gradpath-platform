"""报考条件账本 API — 技能树转型的核心闭环：目标职位条件清单 + 勾选进度 + 完成率。

条件清单由职位表数据规则生成（零录入），用户逐条勾选
unmet/in_progress/met，完成率即北极星指标「条件完成率」的职位级视图。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.gwy_position import GwyPosition
from app.models.user import User
from app.schemas.user_condition import (
    ConditionChecklistResponse,
    ConditionStatusUpdateRequest,
)
from app.services.condition_checklist_service import (
    build_checklist_response,
    build_conditions,
    upsert_status,
)

router = APIRouter(prefix="/api/condition-checklist", tags=["报考条件账本"])


@router.get("/{position_id}", response_model=ConditionChecklistResponse)
def get_checklist(
    position_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取目标职位的条件清单与当前用户核对进度。"""
    position = db.get(GwyPosition, position_id)
    if not position:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "职位不存在")
    return build_checklist_response(db, user.id, position)


@router.put("/status", response_model=ConditionChecklistResponse)
def update_condition_status(
    data: ConditionStatusUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """勾选一条条件的完成状态，返回更新后的完整清单与完成率。"""
    position = db.get(GwyPosition, data.position_id)
    if not position:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "职位不存在")
    valid_keys = {c.key for c in build_conditions(position)}
    if data.condition_key not in valid_keys:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "条件键不在该职位的条件清单中")
    try:
        upsert_status(db, user.id, data.position_id, data.condition_key, data.status)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return build_checklist_response(db, user.id, position)
