"""爬虫定时任务时区测试：seed_default_schedules 必须显式传 timezone=BEIJING_TZ。

容器时区是 UTC——不显式给 timezone，cron 的 02:00 会按 UTC 02:00 触发
=北京时间 10:00。写法仿 tests/test_reminder_d2.py 的 FakeScheduler 范式。
"""

import app.api.crawlers as crawlers
from app.api.crawlers import DEFAULT_DAILY_SCHEDULES, seed_default_schedules
from app.utils.business_time import BEIJING_TZ


class _FakeScheduler:
    def __init__(self):
        self.captured = []

    def get_job(self, job_id):
        return None

    def add_job(self, fn, trigger, **kwargs):
        self.captured.append({"fn": fn, "trigger": trigger, **kwargs})


def test_seed_default_schedules_registers_beijing_timezone(monkeypatch):
    """死规矩：爬虫定时 job 注册时 add_job 必须收到 timezone == BEIJING_TZ。"""
    fake = _FakeScheduler()
    monkeypatch.setattr(crawlers, "get_scheduler", lambda: fake)

    seed_default_schedules()

    assert len(fake.captured) == len(DEFAULT_DAILY_SCHEDULES)
    for kwargs in fake.captured:
        assert kwargs["timezone"] == BEIJING_TZ, (
            "爬虫定时 job 未显式指定北京时区（UTC 容器会错位 8 小时）"
        )
        assert kwargs["trigger"] == "cron"


def test_seed_default_schedules_covers_all_sources(monkeypatch):
    """每个默认源都注册一个 job，且 id 规范为 crawler_{source}。"""
    fake = _FakeScheduler()
    monkeypatch.setattr(crawlers, "get_scheduler", lambda: fake)

    seed_default_schedules()

    ids = {kwargs["id"] for kwargs in fake.captured}
    assert ids == {f"crawler_{source}" for source in DEFAULT_DAILY_SCHEDULES}
