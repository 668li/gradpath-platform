"""P1 中断次日提醒测试：

- 筛选逻辑：昨天完成任务、今天还没开始的用户才收到提醒
- 同一用户同一天最多 1 条
- 开关 MICRO_ACTION_REMINDER_D2 默认 False；测试环境不注册真实 job
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.config import settings
from app.models.micro_action import MicroActionPlan, MicroActionTask
from app.models.notification import Notification
from app.models.streak import StreakRecord
from app.models.user import User
from app.services import reminder_service
from app.services.reminder_service import (
    REMINDER_JOB_ID,
    find_d2_reminder_users,
    register_d2_reminder_job,
)


def _make_user(db_session, email: str) -> User:
    user = User(email=email, password_hash="x", name="提醒测试")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_plan_with_task(
    db_session,
    user: User,
    *,
    completed_yesterday: bool,
    task_status: str = "completed",
):
    plan = MicroActionPlan(user_id=user.id, target_path="employment", status="active")
    db_session.add(plan)
    db_session.flush()

    yesterday = datetime.now().astimezone() - timedelta(days=1)
    task = MicroActionTask(
        plan_id=plan.id,
        day_number=1,
        task_type="research",
        title="查 3 个目标 JD",
        description="描述",
        estimated_minutes=20,
        status=task_status,
        completed_at=yesterday if completed_yesterday else None,
    )
    db_session.add(task)
    db_session.commit()
    return plan, task


# ----------------------------------------------------------------------
# 筛选逻辑
# ----------------------------------------------------------------------


def test_d2_user_with_task_yesterday_and_no_activity_today(db_session):
    """昨天完成任务 + 今天无任何 StreakRecord → 应被筛选出来。"""
    user = _make_user(db_session, "d2-hit@example.com")
    _make_plan_with_task(db_session, user, completed_yesterday=True)

    result = find_d2_reminder_users(db_session)
    assert user.id in result


def test_d2_user_already_active_today_excluded(db_session):
    """今天已有 StreakRecord（已开始行动）→ 不打扰。"""
    user = _make_user(db_session, "d2-active@example.com")
    _make_plan_with_task(db_session, user, completed_yesterday=True)
    db_session.add(
        StreakRecord(
            user_id=user.id,
            activity_date=datetime.now().astimezone().date(),
            activity_types=["main"],
            streak_count=3,
        )
    )
    db_session.commit()

    result = find_d2_reminder_users(db_session)
    assert user.id not in result


def test_d2_user_no_task_yesterday_excluded(db_session):
    """昨天没完成任务（任务 pending）→ 不提醒。"""
    user = _make_user(db_session, "d2-no-task@example.com")
    _make_plan_with_task(
        db_session, user, completed_yesterday=False, task_status="pending"
    )

    result = find_d2_reminder_users(db_session)
    assert user.id not in result


def test_d2_same_day_only_one_reminder(db_session):
    """今天已发过 reminder → 同一天最多 1 条，不再进筛选结果。"""
    user = _make_user(db_session, "d2-dup@example.com")
    _make_plan_with_task(db_session, user, completed_yesterday=True)
    db_session.add(
        Notification(
            user_id=user.id,
            type="reminder",
            title="早前的提醒",
            content="同一天已有一条",
        )
    )
    db_session.commit()

    result = find_d2_reminder_users(db_session)
    assert user.id not in result


def test_d2_user_without_active_plan_excluded(db_session):
    """plan 非 active（已放弃）→ 不提醒。"""
    user = _make_user(db_session, "d2-abandoned@example.com")
    plan = MicroActionPlan(user_id=user.id, target_path="employment", status="abandoned")
    db_session.add(plan)
    db_session.flush()
    db_session.add(
        MicroActionTask(
            plan_id=plan.id,
            day_number=1,
            task_type="research",
            title="任务",
            description="描述",
            estimated_minutes=20,
            status="completed",
            completed_at=datetime.now().astimezone() - timedelta(days=1),
        )
    )
    db_session.commit()

    result = find_d2_reminder_users(db_session)
    assert user.id not in result


# ----------------------------------------------------------------------
# 开关与环境
# ----------------------------------------------------------------------


def test_reminder_flag_default_off():
    """死规矩：MICRO_ACTION_REMINDER_D2 默认 False。"""
    assert settings.MICRO_ACTION_REMINDER_D2 is False


def test_register_job_skipped_when_flag_off(monkeypatch):
    """开关关闭时不注册任何 scheduler job。"""
    monkeypatch.setattr(settings, "MICRO_ACTION_REMINDER_D2", False)
    called = {"scheduler": False}

    class _FakeScheduler:
        def get_job(self, job_id):
            called["scheduler"] = True
            return None

    import app.api.crawlers as crawlers

    monkeypatch.setattr(crawlers, "get_scheduler", lambda: _FakeScheduler())
    register_d2_reminder_job()
    # 关键：开关关闭时根本不应触碰 scheduler
    assert called["scheduler"] is False


def test_register_job_registers_21h_when_enabled(monkeypatch):
    """开关开启 + 非测试环境 → 注册 21:00 的幂等 job。"""
    monkeypatch.setattr(settings, "MICRO_ACTION_REMINDER_D2", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    captured = {}

    class _FakeScheduler:
        def get_job(self, job_id):
            return None

        def add_job(self, fn, trigger, *, id, replace_existing, **kwargs):
            captured["id"] = id
            captured["trigger"] = trigger
            captured.update(kwargs)

    import app.api.crawlers as crawlers

    monkeypatch.setattr(crawlers, "get_scheduler", lambda: _FakeScheduler())
    register_d2_reminder_job()
    assert captured["id"] == REMINDER_JOB_ID
    assert captured["trigger"] == "cron"
    assert captured["hour"] == 21
    assert captured["minute"] == 0


def test_register_job_noop_in_test_env(monkeypatch):
    """死规矩：测试环境不触发真实 job（即使开关开着也不注册）。"""
    monkeypatch.setattr(settings, "MICRO_ACTION_REMINDER_D2", True)
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    called = {"scheduler": False}

    class _FakeScheduler:
        def get_job(self, job_id):
            called["scheduler"] = True
            return None

    import app.api.crawlers as crawlers

    monkeypatch.setattr(crawlers, "get_scheduler", lambda: _FakeScheduler())
    register_d2_reminder_job()
    assert called["scheduler"] is False
