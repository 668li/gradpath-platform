"""AI 周报草稿服务 — 基于用户行为数据自动生成周报。

4层模板：数据层→对比层→洞察层→行动层
叫"草稿"不叫"周报"——用户是作者，AI 是助手。
"""
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.career_plan import CareerPlan
from app.models.milestone_log import MilestoneLog
from app.models.streak import StreakRecord
from app.models.retrospective import Retrospective


def _week_range(today: date = None):
    """返回本周一和下周一（左闭右开）。"""
    d = today or date.today()
    monday = d - timedelta(days=d.weekday())
    week_start = datetime.combine(monday, datetime.min.time())
    next_monday = datetime.combine(monday + timedelta(days=7), datetime.min.time())
    return week_start, next_monday, monday


def generate_weekly_draft(db: Session, user_id: UUID) -> dict:
    """基于本周行为数据生成4层周报草稿。"""
    today = date.today()
    week_start, next_monday, monday = _week_range(today)
    week_end = monday + timedelta(days=6)

    # ─── 数据层：本周行动统计 ───
    week_records = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date >= monday,
            StreakRecord.activity_date <= week_end,
        )
        .order_by(StreakRecord.activity_date.asc())
        .all()
    )

    active_days = len(week_records)
    total_actions = sum(len(r.activity_types) for r in week_records)
    rest_days = sum(1 for r in week_records if r.is_rest_day)
    redeem_days = sum(1 for r in week_records if r.is_redeem)
    main_actions = sum(1 for r in week_records if "main" in r.activity_types)
    micro_actions = sum(1 for r in week_records if "micro" in r.activity_types)
    total_xp = sum(r.xp_earned or 0 for r in week_records)

    # 行动类型分布
    type_distribution: dict[str, int] = {}
    for r in week_records:
        for t in r.activity_types:
            if t not in ("main", "micro", "rest"):
                type_distribution[t] = type_distribution.get(t, 0) + 1

    # 关键事件
    key_events: list[str] = []
    if main_actions > 0:
        key_events.append(f"完成{main_actions}个主行动")
    if micro_actions > 0:
        key_events.append(f"完成{micro_actions}个微行动")
    if rest_days > 0:
        key_events.append(f"休息{rest_days}天")
    if redeem_days > 0:
        key_events.append("回赎断签1次")

    # 本周Streak趋势
    streak_trend = [r.streak_count for r in week_records]
    streak_start = streak_trend[0] if streak_trend else 0
    streak_end = streak_trend[-1] if streak_trend else 0
    streak_change = streak_end - streak_start

    data_layer = {
        "active_days": active_days,
        "total_actions": total_actions,
        "main_actions": main_actions,
        "micro_actions": micro_actions,
        "rest_days": rest_days,
        "total_xp": total_xp,
        "type_distribution": type_distribution,
        "key_events": key_events,
        "streak_start": streak_start,
        "streak_end": streak_end,
        "streak_change": streak_change,
    }

    # ─── 对比层：vs 上周 ───
    last_week_start = monday - timedelta(days=7)
    last_week_end = monday - timedelta(days=1)
    last_week_records = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date >= last_week_start,
            StreakRecord.activity_date <= last_week_end,
        )
        .all()
    )

    last_week_active = len(last_week_records)
    last_week_actions = sum(len(r.activity_types) for r in last_week_records)
    last_week_xp = sum(r.xp_earned or 0 for r in last_week_records)

    comparison_layer = {
        "vs_last_week": {
            "active_days": active_days - last_week_active,
            "total_actions": total_actions - last_week_actions,
            "total_xp": total_xp - last_week_xp,
        },
        "vs_last_week_active": last_week_active,
        "vs_last_week_actions": last_week_actions,
    }

    # ─── 洞察层：基于数据生成AI洞察（最多2条） ───
    insights: list[dict] = []

    # 洞察1：行动集中度
    if total_actions > 0 and main_actions > 0:
        main_pct = round(main_actions / total_actions * 100) if total_actions > 0 else 0
        if main_pct > 70:
            insights.append({
                "text": f"行动{main_pct}%集中在主行动，建议留出时间做微行动（暗知识/档案补全）来保持长期动力",
                "evidence": f"本周{main_actions}个主行动 vs {micro_actions}个微行动",
                "action_link": "/intel",
            })
        elif main_pct < 30 and micro_actions > 0:
            insights.append({
                "text": "微行动占比偏高，下周尝试每天完成1个主行动来推进核心目标",
                "evidence": f"本周{main_actions}个主行动 vs {micro_actions}个微行动",
                "action_link": "/decisions",
            })

    # 洞察2：对比上周
    if last_week_active > 0:
        if active_days > last_week_active:
            insights.append({
                "text": f"比上周多活跃{active_days - last_week_active}天，势头在上升",
                "evidence": f"上周{last_week_active}天 → 本周{active_days}天",
                "action_link": None,
            })
        elif active_days < last_week_active and active_days > 0:
            insights.append({
                "text": f"比上周少活跃{last_week_active - active_days}天，下周只改一件事的话，从周一恢复行动开始",
                "evidence": f"上周{last_week_active}天 → 本周{active_days}天",
                "action_link": "/retrospectives",
            })

    # 限制最多2条
    insights = insights[:2]

    # ─── 行动层：下周建议 ───
    action_layer: list[dict] = []

    if active_days < 5:
        action_layer.append({
            "action": "本周活跃天数不足5天，下周目标：每天至少完成1个微行动",
            "why": "连续行动比单次大行动更能建立习惯",
            "deadline": (week_end + timedelta(days=7)).isoformat(),
            "source": "insight",
        })

    if total_actions > 0 and micro_actions == 0 and main_actions > 0:
        action_layer.append({
            "action": "尝试每天加1个5分钟微行动（看暗知识/补档案）",
            "why": "微行动降低启动门槛，休息日也能保持streak",
            "deadline": (week_end + timedelta(days=7)).isoformat(),
            "source": "insight",
        })

    # 目标锚定：从职业规划中提取下周目标
    plans = (
        db.query(CareerPlan)
        .filter(CareerPlan.user_id == user_id, CareerPlan.status == "active")
        .order_by(CareerPlan.created_at.desc())
        .limit(1)
        .all()
    )
    if plans:
        plan = plans[0]
        action_layer.append({
            "action": f"回顾你的目标「{plan.goal_text[:30]}」，下周推进1个里程碑",
            "why": "目标锚定，保持方向感",
            "deadline": (week_end + timedelta(days=7)).isoformat(),
            "source": "goal",
        })

    action_layer = action_layer[:3]

    return {
        "week_start": monday.isoformat(),
        "week_end": week_end.isoformat(),
        "data_layer": data_layer,
        "comparison_layer": comparison_layer,
        "insight_layer": insights,
        "action_layer": action_layer,
    }