from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.career_event import CareerEvent
from app.models.career_plan import CareerPlan
from app.models.destination_decision import DestinationDecision
from app.models.milestone_log import MilestoneLog
from app.models.retrospective import Retrospective
from app.models.skill_node import SkillNode


def get_overview(db: Session, user_id: UUID) -> dict:
    # 记录每日打卡（打开看板即视为活跃）
    from app.services.streak_service import record_activity
    record_activity(db, user_id, "dashboard")

    decisions = (
        db.query(DestinationDecision)
        .filter(DestinationDecision.user_id == user_id)
        .order_by(DestinationDecision.decision_date.desc())
        .limit(20)
        .all()
    )
    events = (
        db.query(CareerEvent)
        .filter(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.event_date.desc())
        .limit(20)
        .all()
    )
    # 优化：用 group_by + count 聚合替代加载全部行，避免 skills 表增长后传输大量数据
    skill_category_counts = (
        db.query(SkillNode.category, func.count(SkillNode.id))
        .filter(SkillNode.user_id == user_id)
        .group_by(SkillNode.category)
        .all()
    )
    skill_categories: dict[str, int] = {cat: cnt for cat, cnt in skill_category_counts}
    skills_count = sum(skill_categories.values())
    retros = (
        db.query(Retrospective)
        .filter(Retrospective.user_id == user_id)
        .order_by(Retrospective.period_end.desc())
        .limit(10)
        .all()
    )

    latest_decision = None
    if decisions:
        d = decisions[0]
        latest_decision = {
            "id": str(d.id),
            "destination_type": d.destination_type.value,
            "status": d.status.value,
            "decision_date": d.decision_date.isoformat(),
        }

    recent_events = [
        {
            "id": str(e.id),
            "title": e.title,
            "event_type": e.event_type.value,
            "event_date": e.event_date.isoformat(),
        }
        for e in events[:5]
    ]

    latest_retro = None
    if retros:
        r = retros[0]
        latest_retro = {
            "id": str(r.id),
            "title": r.title,
            "period_end": r.period_end.isoformat(),
        }

    # 合并 timeline
    timeline = []
    for d in decisions:
        detail = d.details or {}
        timeline.append({
            "id": str(d.id),
            "date": d.decision_date.isoformat(),
            "type": "decision",
            "title": f"去向决策: {d.destination_type.value}",
            "subtitle": detail.get("company") or detail.get("target_school") or "",
        })
    for e in events:
        timeline.append({
            "id": str(e.id),
            "date": e.event_date.isoformat(),
            "type": "event",
            "title": e.title,
            "subtitle": e.event_type.value,
        })
    timeline.sort(key=lambda x: x["date"], reverse=True)

    return {
        "decisions_count": len(decisions),
        "events_count": len(events),
        "skills_count": skills_count,
        "retrospectives_count": len(retros),
        "latest_decision": latest_decision,
        "recent_events": recent_events,
        "skill_categories": skill_categories,
        "latest_retrospective": latest_retro,
        "timeline": timeline,
    }


def get_weekly_recap(db: Session, user_id: UUID) -> dict:
    """周回顾：本周完成的里程碑、本周新增日志、即将到期里程碑等。

    - 本周范围：周一 00:00:00 到下周一 00:00:00（左闭右开）。
    - completed_this_week：status=="done" 且本周有执行日志的里程碑数
      （以 MilestoneLog.created_at 落在本周作为完成活动信号）。
    - logs_this_week：本周新增的 MilestoneLog 数量。
    - upcoming_deadlines：未来 7 天内（含今天）有 target_date 且
      pending/in_progress 的里程碑。
    - active_plans：status=="active" 的规划数。
    - total_milestones_done / total_milestones：全部规划里程碑统计。
    """
    today = datetime.utcnow().date()
    monday = today - timedelta(days=today.weekday())  # weekday(): Monday=0
    week_start = datetime.combine(monday, datetime.min.time())
    next_monday = datetime.combine(monday + timedelta(days=7), datetime.min.time())
    horizon = today + timedelta(days=7)

    plans = (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id)
        .order_by(CareerPlan.created_at.desc())
        .all()
    )
    user_plan_ids = {str(p.id) for p in plans}

    active_plans = sum(1 for p in plans if p.status == "active")
    total_milestones = 0
    total_milestones_done = 0
    upcoming_deadlines: list[dict] = []
    done_indices_per_plan: dict[str, set[int]] = {}

    for plan in plans:
        milestones = plan.milestones or []
        plan_done: set[int] = set()
        for idx, m in enumerate(milestones):
            if not isinstance(m, dict):
                continue
            total_milestones += 1
            status = m.get("status", "")
            if status == "done":
                total_milestones_done += 1
                plan_done.add(idx)

            # 即将到期：pending/in_progress 且 target_date 在未来 7 天内（含今天）
            if status in ("pending", "in_progress"):
                date_str = m.get("target_date") or m.get("deadline")
                if not date_str:
                    continue
                try:
                    target_date = datetime.strptime(str(date_str), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    continue
                if today <= target_date <= horizon:
                    upcoming_deadlines.append(
                        {
                            "plan_id": str(plan.id),
                            "plan_goal": plan.goal_text,
                            "milestone_title": m.get("title", ""),
                            "milestone_index": idx,
                            "target_date": str(date_str),
                            "days_remaining": (target_date - today).days,
                        }
                    )
        done_indices_per_plan[str(plan.id)] = plan_done

    # 本周新增的执行日志（仅统计属于当前用户的规划）
    logs_query = db.query(MilestoneLog).filter(
        MilestoneLog.created_at >= week_start,
        MilestoneLog.created_at < next_monday,
    )
    if user_plan_ids:
        logs_query = logs_query.filter(MilestoneLog.plan_id.in_(user_plan_ids))
    week_logs = logs_query.all()

    # 按规划聚合本周日志涉及的里程碑索引
    week_log_indices: dict[str, set[int]] = {}
    for log in week_logs:
        key = str(log.plan_id) if not isinstance(log.plan_id, str) else log.plan_id
        week_log_indices.setdefault(key, set()).add(log.milestone_index)

    completed_this_week = 0
    for plan_id, done_indices in done_indices_per_plan.items():
        completed_this_week += len(done_indices & week_log_indices.get(plan_id, set()))

    if completed_this_week > 0:
        encouragement = f"本周已完成{completed_this_week}个里程碑，保持势头！"
    else:
        encouragement = "本周还没有进展，从一个小任务开始吧！"

    return {
        "completed_this_week": completed_this_week,
        "logs_this_week": len(week_logs),
        "upcoming_deadlines": upcoming_deadlines,
        "active_plans": active_plans,
        "total_milestones_done": total_milestones_done,
        "total_milestones": total_milestones,
        "encouragement": encouragement,
    }
