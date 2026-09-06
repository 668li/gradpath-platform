"""业务日基准测试：连击系统以北京时间为准（修复 UTC 容器 0-8 点记错日期）。

- 禁止 mock datetime.now / date.today，一律通过 today 参数注入固定日期。
- 模拟场景：北京时间 00:30 行动时，UTC 还是"昨天"，落库必须是北京日期。
"""

from datetime import date, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.models.user import User
from app.services.streak_service import _week_start, record_activity
from app.utils.business_time import BEIJING_TZ, beijing_today


def _make_user(db_session) -> User:
    user = User(
        email=f"bt-{uuid4()}@example.com",
        password_hash="test-hash",
        name="业务日测试用户",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def test_beijing_today_returns_date():
    """beijing_today() 返回 date 类型，且与 Asia/Shanghai 当前日期一致。"""
    result = beijing_today()
    assert isinstance(result, date)
    expected = datetime.now(BEIJING_TZ).date()
    assert result == expected


def test_record_activity_uses_injected_date_not_utc_date(db_session):
    """北京时间 00:30 行动（UTC 仍是昨天）：落库 activity_date=注入的北京日期。

    固定日期 2026-09-05：对应 UTC 2026-09-04 16:30 —— UTC 日历仍是 9 月 4 日，
    北京日历已是 9 月 5 日。修复前 date.today() 在 UTC 容器会记到 9 月 4 日。
    """
    user = _make_user(db_session)
    beijing_date = date(2026, 9, 5)  # 北京"今天"；此刻 UTC"昨天"= 2026-09-04

    record = record_activity(db_session, user.id, "main", xp=10, today=beijing_date)

    assert record.activity_date == beijing_date, (
        "北京时间 00:30 的行动必须记到北京日期（UTC 日期基准缺陷回归测试）"
    )
    wrong = (
        db_session.query(type(record))
        .filter(
            type(record).user_id == user.id,
            type(record).activity_date == date(2026, 9, 4),
        )
        .first()
    )
    assert wrong is None, "不得把行动记到 UTC 的'昨天'（2026-09-04）"


def test_consecutive_days_streak_increments(db_session):
    """相邻两天各 record_activity 一次 → streak_count 从 1 递增到 2。"""
    user = _make_user(db_session)
    day1 = date(2026, 9, 4)
    day2 = date(2026, 9, 5)

    r1 = record_activity(db_session, user.id, "main", xp=10, today=day1)
    assert r1.streak_count == 1

    r2 = record_activity(db_session, user.id, "micro", xp=3, today=day2)
    assert r2.streak_count == 2
    assert r2.activity_date == day2


def test_week_start_accepts_injected_date():
    """_week_start 注入固定日期返回该周周一（参数注入，不依赖系统时钟）。"""
    wednesday = date(2026, 9, 2)  # 周三
    monday = _week_start(wednesday)
    assert monday == date(2026, 8, 31)
    assert monday.weekday() == 0
