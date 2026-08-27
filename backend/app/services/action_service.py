"""行动任务中心 Service — 行动清单 / 创建 / 更新 / 打卡 / 连击 / 权重。

对齐系统设计 §3.2.M2 行动任务中心契约（方案 C 做实）。

幂等约定：
- 创建行动：X-Idempotency-Key → t_action.biz_req_no，命中返回已有行动
- 行动打卡：X-Idempotency-Key → t_action_checkin.biz_req_no（唯一索引兜底），
  命中返回已有打卡记录；缺省时服务端生成 UUID
"""

import logging
import uuid
from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.action_center import ActionCheckin, ActionStreak, ActionWeight, DailyAction
from app.models.growth_center import GrowthTrajectory
from app.schemas.action import ActionCreateRequest, ActionUpdateRequest, CheckinRequest

logger = logging.getLogger(__name__)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _get_action(db: Session, user_id: UUID, action_id: int) -> DailyAction:
    action = (
        db.query(DailyAction)
        .filter(
            DailyAction.id == action_id,
            DailyAction.user_id == user_id,
            DailyAction.deleted.is_(False),
        )
        .first()
    )
    if action is None:
        raise _not_found("行动不存在")
    return action


def list_today_actions(db: Session, user_id: UUID, today: date | None = None) -> list[DailyAction]:
    """今日行动清单：按权重降序、创建时间升序。"""
    day = today or datetime.now(timezone.utc).date()
    return (
        db.query(DailyAction)
        .filter(
            DailyAction.user_id == user_id,
            DailyAction.deleted.is_(False),
            DailyAction.due_date == day,
        )
        .order_by(DailyAction.weight.desc(), DailyAction.created_time.asc())
        .all()
    )


def create_action(
    db: Session,
    user_id: UUID,
    data: ActionCreateRequest,
    idempotency_key: str | None = None,
) -> DailyAction:
    """创建行动项。

    幂等：idempotency_key 命中 t_action.biz_req_no 时返回已有行动。
    注：ActionCreateRequest.note / biz_fields 契约无存储列，创建时忽略（docstring 声明）。
    """
    if idempotency_key:
        existing = db.query(DailyAction).filter(DailyAction.biz_req_no == idempotency_key).first()
        if existing:
            return existing

    # 唯一约束（user_id, action_type, due_date）：同用户同天同类型只允许一条
    dup = (
        db.query(DailyAction)
        .filter(
            DailyAction.user_id == user_id,
            DailyAction.action_type == data.action_type,
            DailyAction.due_date == data.due_date,
            DailyAction.deleted.is_(False),
        )
        .first()
    )
    if dup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="同一天同一类型的行动已存在",
        )

    # 权重取自 t_action_weight 配置（幂等种子保障），缺失回退默认 1
    from app.seed.seed_action_weight import seed_action_weight

    seed_action_weight(db)
    weight_row = db.query(ActionWeight).filter(ActionWeight.action_type == data.action_type).first()
    weight = weight_row.weight if weight_row else 1

    action = DailyAction(
        user_id=user_id,
        action_type=data.action_type,
        title=data.title,
        due_date=data.due_date,
        source_decision_id=data.source_decision_id,
        weight=weight,
        status="PENDING",
        biz_req_no=idempotency_key,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def update_action(
    db: Session,
    user_id: UUID,
    action_id: int,
    data: ActionUpdateRequest,
) -> DailyAction:
    """更新行动项（部分更新）。

    注：data.note 契约无存储列，更新时忽略（docstring 声明）。
    """
    action = _get_action(db, user_id, action_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        if key == "note":  # 契约无存储列
            continue
        setattr(action, key, value)
    db.commit()
    db.refresh(action)
    return action


def _refresh_streak(db: Session, user_id: UUID, checkin_date: date) -> ActionStreak:
    """打卡后刷新连击统计（连击计算 + ACTIVE/BROKEN/NEVER 状态）。"""
    today = datetime.now(timezone.utc).date()
    streak = db.query(ActionStreak).filter(ActionStreak.user_id == user_id).first()
    if streak is None:
        streak = ActionStreak(
            user_id=user_id,
            current_streak_days=1,
            longest_streak_days=1,
            last_checkin_date=checkin_date,
            streak_status="ACTIVE",
        )
        db.add(streak)
        db.commit()
        db.refresh(streak)
        return streak

    last = streak.last_checkin_date
    if last != checkin_date:  # 同日重复打卡不重复计连击
        if last is not None and (checkin_date - last).days == 1:
            streak.current_streak_days += 1
        else:
            streak.current_streak_days = 1
        streak.longest_streak_days = max(streak.longest_streak_days, streak.current_streak_days)
        streak.last_checkin_date = checkin_date
    # 状态相对「今天」判定：昨天/今天打卡为 ACTIVE，间隔为 BROKEN
    streak.streak_status = "ACTIVE" if (today - checkin_date).days <= 1 else "BROKEN"
    db.commit()
    db.refresh(streak)
    return streak


def checkin_action(
    db: Session,
    user_id: UUID,
    action_id: int,
    data: CheckinRequest,
    idempotency_key: str | None = None,
) -> ActionCheckin:
    """行动打卡。

    幂等：biz_req_no（X-Idempotency-Key，缺省服务端生成 UUID）命中
    t_action_checkin.biz_req_no 唯一索引时返回已有记录。
    联动：刷新连击统计 + 写成长轨迹（event_type=action_checkin）+ 行动置 DONE。
    """
    biz_req_no = idempotency_key or uuid.uuid4().hex
    if idempotency_key:
        existing = (
            db.query(ActionCheckin)
            .filter(
                ActionCheckin.biz_req_no == idempotency_key,
                ActionCheckin.user_id == user_id,
            )
            .first()
        )
        if existing:
            return existing

    action = _get_action(db, user_id, action_id)

    checkin = ActionCheckin(
        action_id=action_id,
        user_id=user_id,
        completed_at=data.completed_at,
        evidence_url=data.evidence_url,
        note=data.note,
        biz_req_no=biz_req_no,
    )
    db.add(checkin)
    db.flush()

    # 联动 1：连击统计
    _refresh_streak(db, user_id, data.completed_at.date())
    # 联动 2：成长轨迹（幂等键复用 biz_req_no）
    db.add(
        GrowthTrajectory(
            user_id=user_id,
            event_type="action_checkin",
            event_payload={
                "action_id": action.id,
                "action_type": action.action_type,
                "title": action.title,
                "weight": action.weight,
                "checkin_id": checkin.id,
                "completed_at": data.completed_at.isoformat(),
                "evidence_url": checkin.evidence_url,
            },
            source_event_id=biz_req_no,
            occurred_at=data.completed_at,
        )
    )
    # 联动 3：行动完成
    action.status = "DONE"
    db.commit()
    db.refresh(checkin)
    return checkin


def list_action_checkins(
    db: Session, user_id: UUID, action_id: int
) -> tuple[list[ActionCheckin], int]:
    """打卡历史（按打卡时间倒序）。"""
    _get_action(db, user_id, action_id)
    query = db.query(ActionCheckin).filter(ActionCheckin.action_id == action_id)
    items = query.order_by(ActionCheckin.completed_at.desc()).all()
    return items, len(items)


def get_streak(db: Session, user_id: UUID) -> ActionStreak | None:
    """查询连击统计；从未打卡返回 None（VO 层回退 NEVER）。"""
    return db.query(ActionStreak).filter(ActionStreak.user_id == user_id).first()


def list_action_weights(db: Session) -> list[ActionWeight]:
    """行动权重表（幂等种子保障 + 按权重升序）。"""
    from app.seed.seed_action_weight import seed_action_weight

    seed_action_weight(db)
    return db.query(ActionWeight).order_by(ActionWeight.weight.asc()).all()
