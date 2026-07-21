"""连续打卡服务层 — 损失厌恶驱动的留存机制。

借鉴 Duolingo 的 streak 设计：
- 易维护的连胜才会被维护
- 计"行动完成"不数"打开"——完成行动才续签
- "1主+1微"双轨：主行动+微行动，完成任一个即续签
- 每周1次休息日，不扣streak
- 断签回赎：完成双倍行动日赎回1次断签
"""
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.streak import StreakRecord

# 里程碑定义
STREAK_MILESTONES = [
    (3, "启动者"),
    (7, "进入节奏"),
    (14, "双周沉淀"),
    (30, "一个月的证据"),
    (60, "赛道坚守者"),
    (100, "长期主义"),
]

# 每周休息日起始（周一）
def _week_start(today: date = None) -> date:
    d = today or date.today()
    return d - timedelta(days=d.weekday())


def record_activity(db: Session, user_id: UUID, activity_type: str, xp: int = 0,
                    action_detail: str = "", is_rest_day: bool = False,
                    is_redeem: bool = False) -> StreakRecord:
    """记录用户当日活跃行为，自动计算连续打卡天数。

    如果当日已有记录，追加行为类型；否则创建新记录并计算 streak。
    """
    today = date.today()

    # 查找当日记录
    record = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date == today,
        )
        .first()
    )

    if record:
        if activity_type not in record.activity_types:
            record.activity_types = [*record.activity_types, activity_type]
        record.xp_earned = (record.xp_earned or 0) + xp
        if action_detail:
            record.action_detail = action_detail
        db.commit()
        db.refresh(record)
        return record

    # 查找昨日记录以计算连续天数
    yesterday = today - timedelta(days=1)
    yesterday_record = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date == yesterday,
        )
        .first()
    )

    if yesterday_record:
        streak_count = yesterday_record.streak_count + 1
    else:
        # 检查前天是否有冻结记录（类似 Duolingo streak freeze）
        day_before = today - timedelta(days=2)
        freeze_record = (
            db.query(StreakRecord)
            .filter(
                StreakRecord.user_id == user_id,
                StreakRecord.activity_date == day_before,
                StreakRecord.freeze_used == True,
            )
            .first()
        )
        if freeze_record:
            streak_count = freeze_record.streak_count + 1
        else:
            streak_count = 1

    record = StreakRecord(
        user_id=user_id,
        activity_date=today,
        activity_types=[activity_type],
        streak_count=streak_count,
        xp_earned=xp,
        is_rest_day=is_rest_day,
        is_redeem=is_redeem,
        action_type=activity_type if not is_rest_day else "rest",
        action_detail=action_detail,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def checkin(db: Session, user_id: UUID, action_type: str = "main",
            action_detail: str = "") -> dict:
    """手动打卡：完成行动后调用。

    action_type: "main" | "micro"
    完成主行动得10XP，微行动得3XP。
    """
    today = date.today()
    existing = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date == today,
        )
        .first()
    )

    xp = 10 if action_type == "main" else 3
    record = record_activity(
        db, user_id, action_type, xp=xp,
        action_detail=action_detail,
    )
    is_new = record.streak_count > 0 and not existing

    return {
        "streak_count": record.streak_count,
        "activity_types": record.activity_types,
        "xp_earned": record.xp_earned,
        "is_new_record": is_new,
    }


def rest_day(db: Session, user_id: UUID) -> dict:
    """每周1次主动标记"今天休息"，不扣streak。"""
    today = date.today()
    ws = _week_start(today)

    # 检查本周是否已使用休息日
    existing_rest = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date >= ws,
            StreakRecord.activity_date <= today,
            StreakRecord.is_rest_day == True,
        )
        .first()
    )

    if existing_rest:
        return {
            "streak_count": existing_rest.streak_count,
            "message": "本周已使用过休息日，每周只能休息1次哦",
        }

    # 获取昨天streak
    yesterday = today - timedelta(days=1)
    yesterday_record = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date == yesterday,
        )
        .first()
    )

    streak_count = yesterday_record.streak_count if yesterday_record else 0

    record = record_activity(
        db, user_id, "rest", xp=0,
        action_detail="休息日",
        is_rest_day=True,
    )
    record.streak_count = streak_count
    db.commit()

    return {
        "streak_count": streak_count,
        "message": "休息日已标记，连胜保持不变。好好休息，明天继续！",
    }


def redeem_streak(db: Session, user_id: UUID) -> dict:
    """断签回赎：完成双倍行动日（主+微都完成）可赎回1次断签。

    条件：昨天断签（昨天无记录），今天完成了主行动+微行动。
    """
    today = date.today()
    yesterday = today - timedelta(days=1)

    # 昨天必须有记录才不算断签
    yesterday_record = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date == yesterday,
        )
        .first()
    )

    if yesterday_record:
        return {
            "streak_count": yesterday_record.streak_count,
            "message": "你没有断签，不需要回赎。继续保持！",
            "redeemed": False,
        }

    # 今天必须有记录（已完成行动）
    today_record = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date == today,
        )
        .first()
    )

    if not today_record:
        return {
            "streak_count": 0,
            "message": "今天还没有完成行动，完成主行动+微行动后可回赎断签",
            "redeemed": False,
        }

    # 检查是否完成了双行动（主+微）
    has_main = "main" in today_record.activity_types
    has_micro = "micro" in today_record.activity_types

    if not (has_main and has_micro):
        return {
            "streak_count": today_record.streak_count,
            "message": "需要完成主行动+微行动（双倍行动日）才能回赎断签",
            "redeemed": False,
        }

    # 回赎：从昨天前天找streak
    day_before = today - timedelta(days=2)
    day_before_record = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date == day_before,
        )
        .first()
    )

    redeemed_count = (day_before_record.streak_count + 1) if day_before_record else 1
    today_record.streak_count = redeemed_count
    today_record.is_redeem = True
    db.commit()

    return {
        "streak_count": redeemed_count,
        "message": f"断签已回赎！连胜恢复至{redeemed_count}天，继续加油！",
        "redeemed": True,
    }


def get_streak_stats(db: Session, user_id: UUID) -> dict:
    """获取用户连续打卡统计（扩展版：含里程碑、休息日、回赎状态）。"""
    today = date.today()
    records = (
        db.query(StreakRecord)
        .filter(StreakRecord.user_id == user_id)
        .order_by(StreakRecord.activity_date.desc())
        .limit(30)
        .all()
    )

    if not records:
        return {
            "current_streak": 0,
            "longest_streak": 0,
            "total_active_days": 0,
            "today_active": False,
            "last_active_date": None,
            "freeze_available": True,
            "recent_records": [],
            "milestones": [{"days": d, "name": n, "unlocked": False} for d, n in STREAK_MILESTONES],
            "rest_day_available": True,
            "redeem_available": False,
        }

    # 当前连续天数
    latest = records[0]
    today_active = latest.activity_date == today

    if not today_active:
        yesterday = today - timedelta(days=1)
        if latest.activity_date == yesterday:
            current_streak = latest.streak_count
        else:
            current_streak = 0
    else:
        current_streak = latest.streak_count

    # 最长连续天数
    longest_streak = max(r.streak_count for r in records)

    # 总活跃天数
    total_count = (
        db.query(StreakRecord)
        .filter(StreakRecord.user_id == user_id)
        .count()
    )

    # 里程碑
    milestones = [
        {"days": d, "name": n, "unlocked": current_streak >= d}
        for d, n in STREAK_MILESTONES
    ]

    # 本周是否已用休息日
    ws = _week_start(today)
    rest_used = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date >= ws,
            StreakRecord.activity_date <= today,
            StreakRecord.is_rest_day == True,
        )
        .first()
    )
    rest_day_available = rest_used is None

    # 回赎是否可用：昨天断签 + 今天完成了双行动
    yesterday = today - timedelta(days=1)
    yesterday_record = (
        db.query(StreakRecord)
        .filter(
            StreakRecord.user_id == user_id,
            StreakRecord.activity_date == yesterday,
        )
        .first()
    )
    redeem_available = False
    if not yesterday_record and today_active:
        has_main = "main" in latest.activity_types
        has_micro = "micro" in latest.activity_types
        redeem_available = has_main and has_micro

    # 最近记录（用于日历展示）
    recent = [
        {
            "date": r.activity_date.isoformat(),
            "streak_count": r.streak_count,
            "activity_types": r.activity_types,
            "xp_earned": r.xp_earned,
            "is_rest_day": r.is_rest_day,
            "is_redeem": r.is_redeem,
            "action_type": r.action_type,
            "action_detail": r.action_detail,
        }
        for r in records[:14]
    ]

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_active_days": total_count,
        "today_active": today_active,
        "last_active_date": latest.activity_date.isoformat(),
        "freeze_available": True,
        "recent_records": recent,
        "milestones": milestones,
        "rest_day_available": rest_day_available,
        "redeem_available": redeem_available,
    }
