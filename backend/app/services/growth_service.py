"""成长档案中心 Service — 轨迹事件流 / 档案聚合 / 实时统计。

对齐系统设计 §3.2.M3 成长档案中心契约（方案 C 做实）。

- 轨迹事件：source_event_id 上游事件幂等 ID，重复提交返回已有事件
- 档案聚合：t_growth_archive 每用户一行（uk_growth_archive_user_id），
  缺失时自动聚合生成；契约 updated_at 无模型列 → 手动映射审计 updated_time
- weighted_action_score：加权行动完成分 = DONE 权重和 / 总权重和 × 100（0~100）
"""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.action_center import ActionStreak, DailyAction
from app.models.growth_center import GrowthArchive, GrowthTrajectory
from app.schemas.growth import (
    GrowthArchiveVO,
    GrowthTrajectoryCreateRequest,
    GrowthTrajectoryVO,
)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def list_trajectory(
    db: Session, user_id: UUID
) -> tuple[list[GrowthTrajectory], int]:
    """成长轨迹时间轴（按事件发生时间倒序）。"""
    items = (
        db.query(GrowthTrajectory)
        .filter(
            GrowthTrajectory.user_id == user_id,
            GrowthTrajectory.deleted.is_(False),
        )
        .order_by(GrowthTrajectory.occurred_at.desc())
        .all()
    )
    return items, len(items)


def create_trajectory(
    db: Session,
    user_id: UUID,
    data: GrowthTrajectoryCreateRequest,
) -> GrowthTrajectory:
    """记录成长轨迹事件。

    幂等：source_event_id 唯一索引（uk_growth_trajectory_source_event_id），
    重复提交返回已有事件。
    """
    if data.source_event_id:
        existing = (
            db.query(GrowthTrajectory)
            .filter(GrowthTrajectory.source_event_id == data.source_event_id)
            .first()
        )
        if existing:
            return existing
    traj = GrowthTrajectory(user_id=user_id, **data.model_dump())
    db.add(traj)
    db.commit()
    db.refresh(traj)
    return traj


def _aggregate(db: Session, user_id: UUID) -> dict:
    """聚合 t_action + t_action_streak，计算档案快照字段。"""
    base_query = db.query(DailyAction).filter(
        DailyAction.user_id == user_id,
        DailyAction.deleted.is_(False),
    )
    total = base_query.count()
    done = (
        base_query.filter(DailyAction.status == "DONE").count()
    )
    rows = db.query(DailyAction.weight, DailyAction.status).filter(
        DailyAction.user_id == user_id,
        DailyAction.deleted.is_(False),
    ).all()
    total_weight = sum(w for w, _ in rows)
    done_weight = sum(w for w, s in rows if s == "DONE")
    streak = db.query(ActionStreak).filter(ActionStreak.user_id == user_id).first()

    return {
        "action_completion_rate": round(done / total, 2) if total else 0.0,
        "total_actions": total,
        "completed_actions": done,
        "streak_days": streak.current_streak_days if streak else 0,
        "weighted_action_score": (
            round(done_weight / total_weight * 100, 2) if total_weight else 0.0
        ),
        "archive_status": "ACTIVE",
    }


def refresh_growth_archive(db: Session, user_id: UUID) -> GrowthArchive:
    """手动触发档案聚合刷新（upsert 单行快照）。"""
    agg = _aggregate(db, user_id)
    archive = (
        db.query(GrowthArchive)
        .filter(GrowthArchive.user_id == user_id)
        .first()
    )
    if archive is None:
        archive = GrowthArchive(user_id=user_id, **agg)
        db.add(archive)
    else:
        for key, value in agg.items():
            setattr(archive, key, value)
    db.commit()
    db.refresh(archive)
    return archive


def get_growth_archive(db: Session, user_id: UUID) -> GrowthArchive:
    """读取档案聚合；缺失时自动聚合生成。"""
    archive = (
        db.query(GrowthArchive)
        .filter(GrowthArchive.user_id == user_id)
        .first()
    )
    if archive is None:
        archive = refresh_growth_archive(db, user_id)
    return archive


def to_archive_vo(archive: GrowthArchive) -> GrowthArchiveVO:
    """档案 VO：契约 updated_at 无模型列 → 手动映射审计 updated_time。"""
    return GrowthArchiveVO(
        user_id=archive.user_id,
        action_completion_rate=float(archive.action_completion_rate or 0),
        total_actions=archive.total_actions,
        completed_actions=archive.completed_actions,
        streak_days=archive.streak_days,
        weighted_action_score=float(archive.weighted_action_score or 0),
        archive_status=archive.archive_status,
        updated_at=archive.updated_time,
    )


def to_trajectory_vo(traj: GrowthTrajectory) -> GrowthTrajectoryVO:
    return GrowthTrajectoryVO(
        id=traj.id,
        user_id=traj.user_id,
        event_type=traj.event_type,
        event_payload=traj.event_payload,
        occurred_at=traj.occurred_at,
        source_event_id=traj.source_event_id,
    )


def get_growth_stats(db: Session, user_id: UUID) -> dict:
    """实时跨表统计（行动完成率 + Streak 统计），不经档案快照。"""
    base_query = db.query(DailyAction).filter(
        DailyAction.user_id == user_id,
        DailyAction.deleted.is_(False),
    )
    total = base_query.count()
    done = base_query.filter(DailyAction.status == "DONE").count()
    streak = db.query(ActionStreak).filter(ActionStreak.user_id == user_id).first()
    return {
        "user_id": user_id,
        "action_completion_rate": round(done / total, 2) if total else 0.0,
        "current_streak_days": streak.current_streak_days if streak else 0,
        "longest_streak_days": streak.longest_streak_days if streak else 0,
        "total_actions": total,
        "completed_actions": done,
    }
