"""行动任务中心 API — 全量做实（鉴权 + 幂等）。

路径与 DTO 对齐系统设计 §3.2.M2.2 接口清单；
user_id 一律由登录态 token 推断（get_current_user），不在请求体传。
"""
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.action import (
    ActionCreateRequest,
    ActionListVO,
    ActionUpdateRequest,
    ActionVO,
    ActionWeightListVO,
    ActionWeightVO,
    CheckinListVO,
    CheckinRequest,
    CheckinVO,
    StreakVO,
)
from app.services import action_service

router = APIRouter(prefix="/api/v1/actions", tags=["行动任务中心"])


@router.get("/today", response_model=ActionListVO)
def get_today_actions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取今日行动清单（按权重降序）。"""
    items = action_service.list_today_actions(db, user.id)
    return ActionListVO(
        items=[ActionVO.model_validate(a) for a in items], total=len(items)
    )


@router.post("", response_model=ActionVO)
def create_action(
    body: ActionCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """生成行动项（幂等：X-Idempotency-Key → t_action.biz_req_no）。"""
    action = action_service.create_action(
        db, user.id, body, idempotency_key=x_idempotency_key
    )
    return ActionVO.model_validate(action)


@router.put("/{action_id}", response_model=ActionVO)
def update_action(
    action_id: int,
    body: ActionUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新行动项（部分更新）。"""
    action = action_service.update_action(db, user.id, action_id, body)
    return ActionVO.model_validate(action)


@router.post("/{action_id}/checkin", response_model=CheckinVO)
def checkin_action(
    action_id: int,
    body: CheckinRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
):
    """行动打卡（幂等：X-Idempotency-Key → biz_req_no，DB 唯一索引兜底）。"""
    checkin = action_service.checkin_action(
        db, user.id, action_id, body, idempotency_key=x_idempotency_key
    )
    return CheckinVO.model_validate(checkin)


@router.get("/{action_id}/checkins", response_model=CheckinListVO)
def list_action_checkins(
    action_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询打卡历史。"""
    items, total = action_service.list_action_checkins(db, user.id, action_id)
    return CheckinListVO(
        items=[CheckinVO.model_validate(c) for c in items], total=total
    )


@router.get("/streaks", response_model=StreakVO)
def get_my_streak(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询连续天数；从未打卡返回 NEVER 占位。"""
    streak = action_service.get_streak(db, user.id)
    if streak is None:
        return StreakVO(
            user_id=user.id,
            current_streak_days=0,
            longest_streak_days=0,
            last_checkin_date=None,
            streak_status="NEVER",
        )
    return StreakVO.model_validate(streak)


@router.get("/weights", response_model=ActionWeightListVO)
def list_action_weights(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询行动权重表（幂等种子保障）。"""
    items = action_service.list_action_weights(db)
    return ActionWeightListVO(
        items=[ActionWeightVO.model_validate(w) for w in items], total=len(items)
    )
