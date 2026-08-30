"""报考条件账本 API — 技能树转型的核心闭环：目标职位条件清单 + 勾选进度 + 完成率。

条件清单由职位表数据规则生成（零录入），用户逐条勾选
unmet/in_progress/met，完成率即北极星指标「条件完成率」的职位级视图。
支持国考（gwy_position）与省考（gwy_province_position）双赛道。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.grad_intel import GradYanzhaoProgram
from app.models.gwy_position import GwyPosition
from app.models.gwy_province_position import GwyProvincePosition
from app.models.user import User
from app.schemas.user_condition import ConditionChecklistResponse, ConditionStatusUpdateRequest
from app.services.condition_checklist_service import (
    build_checklist_response,
    build_conditions,
    build_kaoyan_conditions,
    build_province_conditions,
    upsert_status,
)

router = APIRouter(prefix="/api/condition-checklist", tags=["报考条件账本"])


def _load_position(db: Session, position_id: str, exam_source: str):
    if exam_source == "province":
        return db.get(GwyProvincePosition, position_id)
    if exam_source == "kaoyan":
        # 兼容 hyphenated UUID 与 32-hex 两种入参（研招目录 API 返回前者）
        import uuid as _uuid

        try:
            return db.get(GradYanzhaoProgram, _uuid.UUID(position_id))
        except (ValueError, AttributeError, TypeError):
            return None
    return db.get(GwyPosition, position_id)


def _position_ref(position) -> str:
    """勾选记录用的职位引用键：考研专业转 32-hex，其余原样（sha256 十六进制）。"""
    import uuid as _uuid

    if isinstance(position, GradYanzhaoProgram):
        return (
            position.id.hex
            if isinstance(position.id, _uuid.UUID)
            else str(position.id).replace("-", "")
        )
    return str(position.id)


def _valid_condition_keys(db: Session, position) -> set[str]:
    if isinstance(position, GwyProvincePosition):
        return {c.key for c in build_province_conditions(position)}
    if isinstance(position, GradYanzhaoProgram):
        return {c.key for c in build_kaoyan_conditions(db, position)}
    return {c.key for c in build_conditions(position)}


@router.get("/{position_id}", response_model=ConditionChecklistResponse)
def get_checklist(
    position_id: str,
    source: str = Query(
        "national",
        pattern="^(national|province|kaoyan)$",
        description="赛道：national=国考 / province=省考 / kaoyan=考研",
    ),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取目标职位的条件清单与当前用户核对进度。"""
    position = _load_position(db, position_id, source)
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
    position = _load_position(db, data.position_id, data.exam_source)
    if not position:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "职位不存在")
    if data.condition_key not in _valid_condition_keys(db, position):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "条件键不在该职位的条件清单中")
    try:
        upsert_status(
            db,
            user.id,
            _position_ref(position),
            data.condition_key,
            data.status,
            exam_source=data.exam_source,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e)) from e
    return build_checklist_response(db, user.id, position)
