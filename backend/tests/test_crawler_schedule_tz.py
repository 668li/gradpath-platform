"""爬虫定时任务时区测试：seed_default_schedules 必须显式传 timezone=BEIJING_TZ。

容器时区是 UTC——不显式给 timezone，cron 的 02:00 会按 UTC 02:00 触发
=北京时间 10:00。写法仿 tests/test_reminder_d2.py 的 FakeScheduler 范式。
B0 补（09-26）：seed 孤儿 job 清理 + 回调运行时查 enabled 两门。
"""

import asyncio
import types

import app.api.crawlers as crawlers
from app.api.crawlers import DEFAULT_DAILY_SCHEDULES, seed_default_schedules
from app.utils.business_time import BEIJING_TZ


class _FakeScheduler:
    def __init__(self, existing_jobs=None):
        self.captured = []
        self.removed = []
        # existing_jobs: [(job_id, cron_str)] —— 模拟 Redis jobstore 里的存量 job
        self.existing = {
            jid: types.SimpleNamespace(id=jid, next_run_time=None)
            for jid, _ in (existing_jobs or [])
        }
        # 供清理段读取的当前 job 视图（add 后同步，语义与真 scheduler 一致）
        self._registry = dict(self.existing)

    def get_job(self, job_id):
        return self._registry.get(job_id)

    def get_jobs(self):
        return list(self._registry.values())

    def add_job(self, fn, trigger, **kwargs):
        self.captured.append({"fn": fn, "trigger": trigger, **kwargs})
        self._registry[kwargs["id"]] = types.SimpleNamespace(
            id=kwargs["id"], next_run_time=None
        )

    def remove_job(self, job_id):
        self.removed.append(job_id)
        self._registry.pop(job_id, None)


def test_seed_default_schedules_registers_beijing_timezone(monkeypatch):
    """死规矩：爬虫定时 job 注册时 add_job 必须收到 timezone == BEIJING_TZ。"""
    fake = _FakeScheduler()
    monkeypatch.setattr(crawlers, "get_scheduler", lambda: fake)

    seed_default_schedules()

    assert len(fake.captured) == len(DEFAULT_DAILY_SCHEDULES)
    for kwargs in fake.captured:
        assert (
            kwargs["timezone"] == BEIJING_TZ
        ), "爬虫定时 job 未显式指定北京时区（UTC 容器会错位 8 小时）"
        assert kwargs["trigger"] == "cron"


def test_seed_default_schedules_covers_all_sources(monkeypatch):
    """每个默认源都注册一个 job，且 id 规范为 crawler_{source}。"""
    fake = _FakeScheduler()
    monkeypatch.setattr(crawlers, "get_scheduler", lambda: fake)

    seed_default_schedules()

    ids = {kwargs["id"] for kwargs in fake.captured}
    assert ids == {f"crawler_{source}" for source in DEFAULT_DAILY_SCHEDULES}


def test_seed_prunes_orphan_jobs_of_disabled_lines(monkeypatch):
    """B0 修复：默认表之外的残留 crawler_* job 必须被清理（停线不复活）。

    09-19 停喂令须手工 hdel 的实锤——seed 此前只增不删。
    """
    orphan = "crawler_gwy_announcement"  # 已退役线：不在 DEFAULT_DAILY_SCHEDULES
    live = next(iter(DEFAULT_DAILY_SCHEDULES))  # 任一默认线
    fake = _FakeScheduler(
        existing_jobs=[(orphan, "* * * * *"), (f"crawler_{live}", "* * * * *")]
    )
    monkeypatch.setattr(crawlers, "get_scheduler", lambda: fake)

    seed_default_schedules()

    assert orphan in fake.removed, "停用线的残留 job 未被 seed 清理"
    assert f"crawler_{live}" not in fake.removed, "默认线 job 不可误清"
    # 清理后注册面恰好等于默认表
    assert set(fake._registry) == {f"crawler_{s}" for s in DEFAULT_DAILY_SCHEDULES}


def test_scheduled_crawler_skips_disabled_line(monkeypatch, caplog):
    """B0 修复：回调运行时查 enabled——停用线即使 job 残留也不投递。"""
    from app.crawlers.line_registry import CrawlerLine

    disabled = CrawlerLine(
        name="official_announce",
        schedule="0 * * * *",
        sla_hours=6,
        entry="",
        window=None,
        enabled=False,
        raw={},
    )
    monkeypatch.setattr(
        crawlers, "is_allowed_crawler", lambda name: True
    )
    monkeypatch.setattr(
        "app.crawlers.line_registry.load_lines",
        lambda: {"official_announce": disabled},
    )

    with caplog.at_level("INFO"):
        asyncio.run(crawlers._run_scheduled_crawler("official_announce"))

    assert any("已停用或未注册" in r.message for r in caplog.records), (
        "停用线被回调投递——enabled 闸未生效"
    )


def test_scheduled_crawler_skips_unregistered_line(monkeypatch, caplog):
    """B0 修复：线未注册（load_lines 空注册）时回调跳过，不再裸投。"""
    monkeypatch.setattr(crawlers, "is_allowed_crawler", lambda name: True)
    monkeypatch.setattr("app.crawlers.line_registry.load_lines", lambda: {})

    with caplog.at_level("INFO"):
        asyncio.run(crawlers._run_scheduled_crawler("official_announce"))

    assert any("已停用或未注册" in r.message for r in caplog.records)
