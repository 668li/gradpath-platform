"""date.today() 全仓清零批测试 — 业务日界一律按北京日历（business_time）。

所有用例通过参数注入固定日期，禁止 mock 时间。
"""

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.models.destination_decision import (
    DecisionStatus,
    DestinationDecision,
    DestinationType,
)
from app.models.user import User
from app.services.ai_quota_service import AIQuotaService
from app.services.assessment_interpret_service import _fresh_from_profile
from app.services.decision_journal_service import get_pending_reviews
from app.services.research_promote import _resolve_year
from app.services.weekly_draft_service import _week_range


# ----------------------------------------------------------------------
# AI 配额：日 key 跟随注入日期（北京日历）
# ----------------------------------------------------------------------


def _quota_svc():
    svc = AIQuotaService.__new__(AIQuotaService)
    svc._redis = None
    svc._quota = 100
    return svc


def test_quota_key_uses_injected_date():
    """注入"UTC 还是昨天、北京已是今天"的日期 → key 用北京日。"""
    beijing_today = date(2026, 9, 5)
    uid = uuid4()
    key = _quota_svc()._quota_key(uid, today=beijing_today)
    assert key.endswith("2026-09-05")


def test_quota_same_day_same_key():
    """同日两次取 key → 同一个 key（配额计数不分裂）。"""
    uid = uuid4()
    d = date(2026, 9, 5)
    assert _quota_svc()._quota_key(uid, today=d) == _quota_svc()._quota_key(uid, today=d)


# ----------------------------------------------------------------------
# 周报：周界按北京周一
# ----------------------------------------------------------------------


def test_week_range_saturday_maps_to_this_monday():
    """周六 → 本周一（2026-09-05 是周六，周一=2026-08-31）。"""
    week_start, next_monday, monday = _week_range(date(2026, 9, 5))
    assert monday == date(2026, 8, 31)
    assert monday.weekday() == 0
    assert next_monday.date() == date(2026, 9, 7)


# ----------------------------------------------------------------------
# 研究日期年份推断：跟随注入的北京今天
# ----------------------------------------------------------------------


def test_resolve_year_future_month_stays_this_year():
    """无年份的 10月9日，北京今天 9-05 → 未来优先 → 今年。"""
    assert _resolve_year(10, 9, today=date(2026, 9, 5)) == 2026


def test_resolve_year_past_month_rolls_next_year():
    """无年份的 3月4日，北京今天 9-05 → 已过 → 次年（复试/调剂场景）。"""
    assert _resolve_year(3, 4, today=date(2026, 9, 5)) == 2027


# ----------------------------------------------------------------------
# 应届判定：年度基准跟随注入
# ----------------------------------------------------------------------


def test_fresh_from_profile_same_year_is_fresh():
    profile = SimpleNamespace(graduation_year=2026)
    assert _fresh_from_profile(profile, today=date(2026, 9, 5)) == "应届"


def test_fresh_from_profile_earlier_year_not_fresh():
    profile = SimpleNamespace(graduation_year=2025)
    assert _fresh_from_profile(profile, today=date(2026, 9, 5)) == "非应届"


# ----------------------------------------------------------------------
# 决策回溯筛选：跟随注入日期
# ----------------------------------------------------------------------


def _make_decision(db_session, user, review_date):
    d = DestinationDecision(
        user_id=user.id,
        decision_date=review_date,
        destination_type=DestinationType.employment,
        status=DecisionStatus.planned,
        details={},
        confidence=70,
        review_date=review_date,
        review_completed=False,
    )
    db_session.add(d)
    db_session.commit()
    return d


def test_pending_reviews_includes_due_today(db_session):
    user = User(email=f"sweep-{uuid4().hex[:8]}@example.com", password_hash="x", name="清扫测试")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    _make_decision(db_session, user, review_date=date(2026, 9, 5))

    result = get_pending_reviews(db_session, user.id, today=date(2026, 9, 5))
    assert len(result) == 1


def test_pending_reviews_excludes_future(db_session):
    user = User(email=f"sweep-{uuid4().hex[:8]}@example.com", password_hash="x", name="清扫测试")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    _make_decision(db_session, user, review_date=date(2026, 9, 6))

    result = get_pending_reviews(db_session, user.id, today=date(2026, 9, 5))
    assert result == []
