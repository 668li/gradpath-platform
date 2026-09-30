"""维护类定时任务回归测试（DF-12，2026-09-29；DF-21，2026-09-30）。

锁定：
- data_freshness 看板可见性：SOURCES 必含 scoreline_official / yanzhao_official
- 年度 job 形状：maintenance_ 前缀（B0 crawler_ 增删平衡不误伤）+ 各自年度 cron
- 心跳回写在 data_freshness 表缺失的开发环境降级不炸（设计行为）
"""

from app.api.data_freshness import SOURCES
from app.tasks.maintenance_tasks import (
    ANNUAL_CRON,
    ANNUAL_JOB_ID,
    YANZHAO_ANNUAL_CRON,
    YANZHAO_ANNUAL_JOB_ID,
    upsert_scoreline_heartbeat,
    upsert_yanzhao_heartbeat,
)


def test_scoreline_official_visible_on_dashboard():
    assert "scoreline_official" in SOURCES, "心跳行不在 SOURCES 映射=看板不可见"


def test_annual_cron_shape():
    assert ANNUAL_CRON == {"month": 3, "day": 15, "hour": 6, "minute": 0}
    assert ANNUAL_JOB_ID.startswith("maintenance_"), (
        "crawler_ 前缀会被 B0 增删平衡清理，维护 job 必须独立前缀"
    )


def test_seed_registers_annual_job(monkeypatch):
    """seed_maintenance_jobs 应向 scheduler 注册年度 job（幂等形状）。"""
    added = {}

    class FakeScheduler:
        def get_job(self, job_id):
            return added.get(job_id)

        def add_job(self, fn, trigger, **kw):
            added[kw["id"]] = (fn, trigger, kw)

    import app.api.crawlers as crawlers

    monkeypatch.setattr(crawlers, "get_scheduler", lambda: FakeScheduler())
    from app.tasks import maintenance_tasks

    monkeypatch.setattr(
        maintenance_tasks, "upsert_scoreline_heartbeat", lambda: None
    )
    monkeypatch.setattr(
        maintenance_tasks, "upsert_yanzhao_heartbeat", lambda: None
    )
    maintenance_tasks.seed_maintenance_jobs()
    assert ANNUAL_JOB_ID in added
    _, trigger, kw = added[ANNUAL_JOB_ID]
    assert trigger == "cron"
    assert kw["month"] == 3 and kw["day"] == 15


def test_yanzhao_official_visible_on_dashboard():
    assert "yanzhao_official" in SOURCES, "心跳行不在 SOURCES 映射=看板不可见"


def test_yanzhao_annual_cron_shape():
    assert YANZHAO_ANNUAL_CRON == {"month": 9, "day": 15, "hour": 6, "minute": 0}
    assert YANZHAO_ANNUAL_JOB_ID.startswith("maintenance_"), (
        "crawler_ 前缀会被 B0 增删平衡清理，维护 job 必须独立前缀"
    )


def test_seed_registers_yanzhao_annual_job(monkeypatch):
    """seed_maintenance_jobs 应同时注册分数线与简章两个年度 job（幂等形状）。"""
    added = {}

    class FakeScheduler:
        def get_job(self, job_id):
            return added.get(job_id)

        def add_job(self, fn, trigger, **kw):
            added[kw["id"]] = (fn, trigger, kw)

    import app.api.crawlers as crawlers

    monkeypatch.setattr(crawlers, "get_scheduler", lambda: FakeScheduler())
    from app.tasks import maintenance_tasks

    monkeypatch.setattr(
        maintenance_tasks, "upsert_scoreline_heartbeat", lambda: None
    )
    monkeypatch.setattr(
        maintenance_tasks, "upsert_yanzhao_heartbeat", lambda: None
    )
    maintenance_tasks.seed_maintenance_jobs()
    assert YANZHAO_ANNUAL_JOB_ID in added
    _, trigger, kw = added[YANZHAO_ANNUAL_JOB_ID]
    assert trigger == "cron"
    assert kw["month"] == 9 and kw["day"] == 15
    assert ANNUAL_JOB_ID in added, "DF-21 改造不得回退 DF-12 的年度 job 注册"


def test_yanzhao_heartbeat_degrades_without_table():
    """开发库无 data_freshness 表时简章心跳回写静默降级（不 raise）。"""
    upsert_yanzhao_heartbeat()  # 不应抛异常


def test_heartbeat_degrades_without_table():
    """开发库无 data_freshness 表时心跳回写静默降级（不 raise）。"""
    upsert_scoreline_heartbeat()  # 不应抛异常
