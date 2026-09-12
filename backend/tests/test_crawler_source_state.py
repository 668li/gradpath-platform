"""地基④⑥测试（spec 002 FR3/FR5，验收判据 3：死而被知）。

- 状态表生命周期：成功清零+游标回写；连续 2 次失败自动隔离；
- 心跳全覆盖：成功 active 累加、失败 status=failed 且 last_successful_crawl 不动；
- 调度闸：隔离源在投递入口（APScheduler 回调）与 worker 侧均被跳过；
- 解除隔离：显式人工动作，未隔离行解除返回 False。
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.crawlers.base_crawler import BaseCrawler
from app.database import Base
from app.models.crawler_state import CrawlerSourceState
from app.models.ingestion import DataFreshness
from app.services import crawler_state_service as svc


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


class _FailingCrawler(BaseCrawler):
    """fetch 必炸的最小爬虫：驱动 run() 失败路径的集成测试。"""

    name = "state_probe"
    category = "test"

    def fetch(self):
        raise RuntimeError("boom")

    def parse(self, raw_items):
        return []

    def store(self, items, db=None):
        return 0


class _EmptyCrawler(_FailingCrawler):
    def fetch(self):
        return []


def test_success_resets_fails_and_writes_heartbeat(db):
    db.add(CrawlerSourceState(source_name="state_probe", consecutive_fails=1))
    db.commit()

    crawler = _EmptyCrawler(config={"rate_limit": 0})
    result = crawler.run(db=db)
    assert result["status"] == "success"

    state = db.query(CrawlerSourceState).filter_by(source_name="state_probe").one()
    assert state.consecutive_fails == 0
    assert state.last_ok_at is not None
    assert state.isolated is False

    fresh = db.query(DataFreshness).filter_by(source_name="state_probe").one()
    assert fresh.status == "active"
    assert fresh.last_successful_crawl is not None


def test_two_consecutive_failures_auto_isolate(db):
    crawler = _FailingCrawler(config={"rate_limit": 0})
    assert crawler.run(db=db)["status"] == "failed"
    assert svc.is_isolated(db, "state_probe") is False, "首次失败不应立即隔离"

    result = crawler.run(db=db)
    assert result["status"] == "failed"
    assert svc.is_isolated(db, "state_probe") is True, "连续 2 次失败必须自动隔离"

    state = db.query(CrawlerSourceState).filter_by(source_name="state_probe").one()
    assert state.consecutive_fails == 2
    assert "连续 2 次运行失败" in state.isolated_reason

    fresh = db.query(DataFreshness).filter_by(source_name="state_probe").one()
    assert fresh.status == "failed", "失败运行的心跳必须如实记录为 failed"
    assert fresh.last_successful_crawl is None


def test_heartbeat_failure_keeps_last_successful(db):
    svc.record_heartbeat(db, "eol_kaoyan", ok=True, inserted=7)
    db.commit()
    ok_at = db.query(DataFreshness).filter_by(source_name="eol_kaoyan").one().last_successful_crawl

    svc.record_heartbeat(db, "eol_kaoyan", ok=False)
    db.commit()
    fresh = db.query(DataFreshness).filter_by(source_name="eol_kaoyan").one()
    assert fresh.status == "failed"
    assert fresh.last_successful_crawl == ok_at, "失败不得推进 last_successful_crawl（老化诚实口径）"
    assert fresh.records_count == 7, "失败不得累加记录数"


def test_unisolate_explicit_only(db):
    assert svc.unisolate(db, "state_probe") is False, "未隔离行解除必须返回 False"

    db.add(CrawlerSourceState(source_name="state_probe", isolated=True, isolated_reason="测试"))
    db.commit()
    assert svc.unisolate(db, "state_probe", by="tester") is True
    state = db.query(CrawlerSourceState).filter_by(source_name="state_probe").one()
    assert state.isolated is False and state.consecutive_fails == 0 and state.isolated_reason is None


def test_cursor_roundtrip(db):
    svc.record_run_result(db, "demo", ok=True, cursor={"etag": "abc123"})
    db.commit()
    assert svc.load_cursor(db, "demo") == {"etag": "abc123"}
    svc.record_run_result(db, "demo", ok=False)
    db.commit()
    assert svc.load_cursor(db, "demo") == {"etag": "abc123"}, "失败运行不得抹掉游标"


def test_scheduler_delivery_gate_skips_isolated(db, monkeypatch):
    """隔离源在调度投递入口被真实跳过（验收判据 3 的闸侧证据）。"""
    import app.api.crawlers as api_crawlers

    db.add(CrawlerSourceState(source_name="eol_kaoyan", isolated=True, isolated_reason="测试隔离"))
    db.commit()

    dispatched: list[str] = []
    monkeypatch.setattr(api_crawlers, "_celery_available", lambda: True)
    import app.tasks.crawler_tasks as tasks

    monkeypatch.setattr(
        type(tasks.run_scheduled_crawler_task),
        "delay",
        lambda self=None, *a, **kw: dispatched.append(a[0] if a else kw.get("source_name")),
        raising=False,
    )
    # 隔离检查使用 api_crawlers 模块级 SessionLocal：指向测试会话工厂
    monkeypatch.setattr(api_crawlers, "SessionLocal", sessionmaker(bind=db.get_bind()))

    asyncio.run(api_crawlers._run_scheduled_crawler("eol_kaoyan"))
    assert dispatched == [], "隔离源必须被调度闸跳过，不得投递"
