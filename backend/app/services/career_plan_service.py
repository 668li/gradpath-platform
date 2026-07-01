# backend/app/services/career_plan_service.py
"""职业规划服务层 — Phase 11 / Phase 12。

提供用户职业规划的列表、详情与里程碑状态更新（Phase 11），
以及里程碑执行日志管理与到期提醒（Phase 12）。
"""
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.career_plan import CareerPlan
from app.models.milestone_log import MilestoneLog


def list_plans(db: Session, user_id: UUID) -> list[CareerPlan]:
    """列出用户的规划（按创建时间倒序）。"""
    return (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id)
        .order_by(CareerPlan.created_at.desc())
        .all()
    )


def get_plan(db: Session, user_id: UUID, plan_id: UUID) -> CareerPlan | None:
    """获取规划详情（验证所有权）。"""
    return (
        db.query(CareerPlan)
        .filter(CareerPlan.id == plan_id, CareerPlan.user_id == user_id)
        .first()
    )


def update_milestone(
    db: Session, user_id: UUID, plan_id: UUID, milestone_idx: int, status: str
) -> CareerPlan | None:
    """更新里程碑状态。

    Args:
        milestone_idx: 里程碑在 milestones 列表中的索引（从 0 开始）
        status: 新状态（pending/in_progress/done）

    Returns:
        更新后的 CareerPlan，若规划不存在或索引越界则返回 None
    """
    plan = get_plan(db, user_id, plan_id)
    if not plan:
        return None

    milestones = plan.milestones or []
    if milestone_idx < 0 or milestone_idx >= len(milestones):
        return None

    # 构建新的里程碑列表（深拷贝以避免原地修改不被追踪）
    new_milestones = []
    for i, m in enumerate(milestones):
        if i == milestone_idx:
            new_m = dict(m) if isinstance(m, dict) else m
            if isinstance(new_m, dict):
                new_m["status"] = status
            new_milestones.append(new_m)
        else:
            new_milestones.append(m)

    plan.milestones = new_milestones
    flag_modified(plan, "milestones")
    db.commit()
    db.refresh(plan)
    return plan


# ======================================================================
# Phase 12: 里程碑执行日志与到期提醒
# ======================================================================

def add_milestone_log(
    db: Session, user_id: UUID, plan_id: UUID, milestone_index: int, content: str
) -> MilestoneLog | None:
    """为指定里程碑添加执行日志。

    验证规划归属当前用户，且 milestone_index 在 milestones 范围内。

    Returns:
        创建的 MilestoneLog；若规划不存在、不属于用户或索引越界则返回 None
    """
    plan = get_plan(db, user_id, plan_id)
    if not plan:
        return None

    milestones = plan.milestones or []
    if milestone_index < 0 or milestone_index >= len(milestones):
        return None

    log = MilestoneLog(
        plan_id=str(plan.id),
        milestone_index=milestone_index,
        content=content,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def list_milestone_logs(
    db: Session, user_id: UUID, plan_id: UUID, milestone_index: int
) -> list[MilestoneLog]:
    """列出指定里程碑的执行日志（按创建时间倒序）。

    验证规划归属当前用户后返回日志列表。
    """
    plan = get_plan(db, user_id, plan_id)
    if not plan:
        return []

    return (
        db.query(MilestoneLog)
        .filter(
            MilestoneLog.plan_id == str(plan.id),
            MilestoneLog.milestone_index == milestone_index,
        )
        .order_by(MilestoneLog.created_at.desc())
        .all()
    )


def delete_milestone_log(db: Session, user_id: UUID, log_id: str) -> MilestoneLog | None:
    """删除一条执行日志。

    通过 log → plan → user_id 验证归属当前用户。

    Returns:
        被删除的 MilestoneLog；若日志不存在或不属于当前用户则返回 None
    """
    log = db.query(MilestoneLog).filter(MilestoneLog.id == log_id).first()
    if not log:
        return None

    # 通过 plan 校验归属（log.plan_id 为字符串，需转为 UUID 以匹配 CareerPlan.id 列）
    try:
        plan_uuid = UUID(log.plan_id)
    except (ValueError, AttributeError, TypeError):
        return None
    plan = (
        db.query(CareerPlan)
        .filter(CareerPlan.id == plan_uuid, CareerPlan.user_id == user_id)
        .first()
    )
    if not plan:
        return None

    db.delete(log)
    db.commit()
    return log


def get_reminders(db: Session, user_id: UUID) -> list[dict]:
    """查询用户的到期提醒。

    遍历用户所有 status=="active" 的 CareerPlan 的 milestones，分类：
    - overdue: target_date 早于今天 且 status != "done"
    - upcoming: target_date 在未来 7 天内（含今天） 且 status != "done"

    兼容 milestone 中的 target_date 与 deadline 两种日期字段名。

    Returns:
        ReminderItem 字典列表
    """
    plans = (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id, CareerPlan.status == "active")
        .all()
    )

    today = datetime.utcnow().date()
    horizon = today + timedelta(days=7)
    reminders: list[dict] = []

    for plan in plans:
        milestones = plan.milestones or []
        for idx, m in enumerate(milestones):
            if not isinstance(m, dict):
                continue
            # 已完成的里程碑不提醒
            if m.get("status") == "done":
                continue

            # 兼容 target_date 与 deadline 字段
            date_str = m.get("target_date") or m.get("deadline")
            if not date_str:
                continue
            try:
                target_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue

            days_remaining = (target_date - today).days

            if target_date < today:
                reminder_type = "overdue"
            elif target_date <= horizon:
                reminder_type = "upcoming"
            else:
                # 超过 7 天，不提醒
                continue

            reminders.append(
                {
                    "plan_id": str(plan.id),
                    "plan_goal": plan.goal_text,
                    "milestone_title": m.get("title", ""),
                    "milestone_index": idx,
                    "target_date": str(date_str),
                    "days_remaining": days_remaining,
                    "type": reminder_type,
                }
            )

    return reminders


def get_daily_focus(db: Session, user_id: UUID) -> list[dict]:
    """获取今日重点：每个 active 规划的当前焦点里程碑。

    对每个 status=="active" 的规划：
    1. 优先取第一个 status=="in_progress" 的里程碑；
    2. 若没有 in_progress，则取第一个 status=="pending" 的里程碑；
    3. 都没有则跳过该规划。

    跨规划汇总后按优先级排序（in_progress 优先于 pending），最多返回 3 条。
    has_logs 标记该里程碑是否已有执行日志（MilestoneLog）。

    Returns:
        DailyFocusItem 字典列表
    """
    plans = (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id, CareerPlan.status == "active")
        .order_by(CareerPlan.created_at.asc())
        .all()
    )

    candidates: list[tuple[int, dict]] = []  # (priority, item)
    for plan in plans:
        milestones = plan.milestones or []
        chosen: tuple[int, dict, int] | None = None  # (idx, milestone, priority)

        # 优先 in_progress（priority=0）
        for idx, m in enumerate(milestones):
            if isinstance(m, dict) and m.get("status") == "in_progress":
                chosen = (idx, m, 0)
                break
        # 其次 pending（priority=1）
        if chosen is None:
            for idx, m in enumerate(milestones):
                if isinstance(m, dict) and m.get("status") == "pending":
                    chosen = (idx, m, 1)
                    break
        if chosen is None:
            continue

        idx, m, priority = chosen
        log_count = (
            db.query(MilestoneLog)
            .filter(
                MilestoneLog.plan_id == str(plan.id),
                MilestoneLog.milestone_index == idx,
            )
            .count()
        )
        candidates.append(
            (
                priority,
                {
                    "plan_id": str(plan.id),
                    "plan_goal": plan.goal_text,
                    "milestone_title": m.get("title", ""),
                    "milestone_index": idx,
                    "milestone_description": m.get("description", ""),
                    "status": m.get("status", ""),
                    "has_logs": log_count > 0,
                },
            )
        )

    # 按优先级排序：in_progress（0）优先于 pending（1）
    candidates.sort(key=lambda x: x[0])
    return [item for _, item in candidates[:3]]
