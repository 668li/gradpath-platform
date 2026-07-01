"""连续打卡服务层 — 损失厌恶驱动的留存机制。

借鉴 Duolingo 的 streak 设计：
- 易维护的连胜才会被维护（任何一次活跃都算打卡）
- 连胜冻结机制（断签后可恢复）
- 活跃行为自动检测（不需要用户手动打卡）
"""
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.streak import StreakRecord

# 冻结额度：每 7 天连续打卡获得 1 次冻结机会
FREEZE_GRANT_INTERVAL = 7


def record_activity(db: Session, user_id: UUID, activity_type: str, xp: int = 0) -> StreakRecord:
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
        # 追加行为类型
        if activity_type not in record.activity_types:
            record.activity_types = [*record.activity_types, activity_type]
        record.xp_earned = (record.xp_earned or 0) + xp
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
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_streak_stats(db: Session, user_id: UUID) -> dict:
    """获取用户连续打卡统计。"""
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
        }

    # 当前连续天数
    latest = records[0]
    today_active = latest.activity_date == today

    # 如果今天没活跃，检查昨天是否活跃（streak 仍有效）
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

    # 冻结可用性：当前 streak >= 7 的倍数时可用
    freeze_available = current_streak > 0 and (current_streak % FREEZE_GRANT_INTERVAL != 0 or current_streak >= FREEZE_GRANT_INTERVAL)

    # 最近记录（用于日历展示）
    recent = [
        {
            "date": r.activity_date.isoformat(),
            "streak_count": r.streak_count,
            "activity_types": r.activity_types,
            "xp_earned": r.xp_earned,
        }
        for r in records[:14]
    ]

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_active_days": total_count,
        "today_active": today_active,
        "last_active_date": latest.activity_date.isoformat(),
        "freeze_available": freeze_available,
        "recent_records": recent,
    }
