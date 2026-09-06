"""爬取记账单行化测试：一次爬取全程恰一行 CrawlerRun + 观测字段齐全。

背景：此前包装层（crawler_tasks / api 兜底）与爬虫 store() 各建一行 CrawlerRun，
同一次爬取落两行（fetched/stored 相同、时间差=爬取时长）。现在行以爬虫内部
创建为准（run_id 溯源链在爬虫手上），包装层只更新该行；爬虫未建行
（dry_run / 建行前失败）时由包装层兜底补一行并回填计时字段。

网络全 mock（不打外网、不走 robots/限速路径）；夹具为内联合法 HTML。
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api import crawlers as api_crawlers  # noqa: E402
from app.crawlers.research.official_announce_crawler import (  # noqa: E402
    OfficialAnnounceCrawler,
)
from app.models.crawler_run import CrawlerRun  # noqa: E402
from app.tasks import crawler_tasks  # noqa: E402

_SECTION = {
    "name": "测试大学研究生院硕士招生",
    "list_url": "https://univ-test.edu.cn/zsgz/sszs.htm",
    "detail_url_re": r"info/\d+/\d+\.htm",
    "content_cls": "v_news_content",
    "title_suffix": "-测试大学研究生院",
}

# 空栏目列表页（0 条）：走包装层成功路径但不触发广播/自动放行
_EMPTY_LIST_HTML = "<html><body><ul><li>本栏目暂无公告</li></ul></body></html>"

_LIST_HTML = """<html><body><ul>
<li><a href="/info/1010/9001.htm">2027年硕士研究生招生简章</a><span>2026-08-01</span></li>
<li><a href="/info/1010/9002.htm">2027年接收推荐免试研究生预报名的通知</a><span>2026-07-15</span></li>
</ul></body></html>"""

_DETAIL_HTML = (
    "<html><head><title>2027年硕士研究生招生简章 - 测试大学研究生院</title></head><body>"
    '<div class="v_news_content">根据教育部有关规定，我校2027年硕士研究生招生考试实行网上报名，'
    "考生应在规定时间内登录研招信息网浏览报考须知，并按教育部、省级教育招生考试机构、"
    "报考点以及我校的网上公告要求报名。逾期不再补报，也不得修改报名信息。</div>"
    "</body></html>"
)


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text
        self.status_code = 200

    def raise_for_status(self) -> None:
        return None


def _fake_body_for(url: str) -> str:
    if url == _SECTION["list_url"]:
        return _LIST_HTML
    if url.endswith("empty.htm"):
        return _EMPTY_LIST_HTML
    return _DETAIL_HTML


def _patched_crawler_cls(base=OfficialAnnounceCrawler, sections=None):
    """构造一个网络全 mock 的爬虫子类（wrapper 内部实例化也走 mock）。"""

    class _Patched(base):
        def _request(self, url, method="GET", **kwargs):
            return _FakeResponse(_fake_body_for(url))

    return _Patched


def _make_config(sections=None) -> dict:
    return {"rate_limit": 0, "fetch_detail": True, "sections": sections or [_SECTION]}


# ===== 爬虫层：run() 全程恰一行 + 观测字段 =====


def test_official_announce_run_single_row(db_session, monkeypatch):
    """本地跑 1 个爬虫（mock 网络）：CrawlerRun 恰 1 行且观测字段齐全。"""
    crawler = OfficialAnnounceCrawler(config=_make_config())
    monkeypatch.setattr(crawler, "_request", lambda url, method="GET", **kw: _FakeResponse(_fake_body_for(url)))

    result = crawler.run(db=db_session)

    assert result["status"] == "success"
    rows = db_session.query(CrawlerRun).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.source_name == "official_announce"
    assert row.status == "success"
    # 观测字段：时间 + 计数
    assert row.started_at
    assert row.finished_at
    assert row.duration_seconds >= 1
    assert row.items_fetched == 2
    assert row.stored_count == result["stored"]
    assert row.stored_count >= 1
    assert row.duplicate_count == result.get("duplicates", 0)
    # 包装层靠 result.run_id 找到爬虫建的这一行
    assert result["run_id"] == str(row.id)


def test_run_twice_creates_one_row_per_run(db_session, monkeypatch):
    """跑两次 = 恰两行（每行对应一次爬取），而非一次爬取内部分裂成两行。"""
    crawler = OfficialAnnounceCrawler(config=_make_config())
    monkeypatch.setattr(crawler, "_request", lambda url, method="GET", **kw: _FakeResponse(_fake_body_for(url)))

    crawler.run(db=db_session)
    crawler.run(db=db_session)

    assert db_session.query(CrawlerRun).count() == 2


# ===== 包装层：更新爬虫建的行，不另建 =====


def _patch_wrapper_env(monkeypatch, db_session, crawler_cls, config):
    monkeypatch.setattr(crawler_tasks, "get_crawler", lambda name: crawler_cls)
    monkeypatch.setattr(crawler_tasks, "load_config", lambda name: config)
    monkeypatch.setattr(crawler_tasks, "SessionLocal", lambda: db_session)
    monkeypatch.setattr(
        crawler_tasks,
        "ws_manager",
        SimpleNamespace(
            notify_task_sync=lambda *a, **k: None,
            broadcast_sync=lambda payload: None,
        ),
    )
    # 自动放行走测试库（真实实现会连生产 SessionLocal）
    monkeypatch.setattr(
        "app.services.research_auto_review.auto_review_pending", lambda db: {"auto_approved": 0}
    )


def test_scheduled_task_wrapper_single_row(db_session, monkeypatch):
    """Celery 定时任务路径：全程恰一行，且为爬虫 store() 建的行。"""
    _patch_wrapper_env(monkeypatch, db_session, _patched_crawler_cls(), _make_config())

    crawler_tasks.run_scheduled_crawler_task.run("official_announce")

    rows = db_session.query(CrawlerRun).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.status == "success"
    assert row.started_at and row.finished_at
    assert row.duration_seconds >= 1
    assert row.stored_count >= 1


def test_scheduled_task_failure_fallback_single_row(db_session, monkeypatch):
    """爬虫建行前失败（parse 抛异常）：兜底补一行，恰一行且 status=failed。"""

    class _Exploding(_patched_crawler_cls()):
        def parse(self, raw_items):
            raise RuntimeError("parse 爆炸")

    _patch_wrapper_env(monkeypatch, db_session, _Exploding, _make_config())

    result = crawler_tasks.run_scheduled_crawler_task.run("official_announce")

    assert result["status"] == "failed"
    rows = db_session.query(CrawlerRun).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.status == "failed"
    assert "parse 爆炸" in (row.error_message or "")
    assert row.duration_seconds >= 1


def test_user_task_dry_run_fallback_single_row(db_session, monkeypatch):
    """用户触发 dry_run：爬虫不建行 → 包装层兜底恰一行。"""
    _patch_wrapper_env(monkeypatch, db_session, _patched_crawler_cls(), _make_config())

    # bind=True 任务：.run 已绑定 self，直接调用即本地执行（避免 apply() 触发
    # memory:// result backend 解析——测试环境无 worker/broker）
    result = crawler_tasks.run_crawler_task.run(uuid4().hex[:12], "official_announce", True)

    assert result["status"] == "dry_run"
    rows = db_session.query(CrawlerRun).all()
    assert len(rows) == 1
    assert rows[0].status == "dry_run"


# ===== API 兜底路径：Celery 不可用分支同样单行 =====


def test_api_scheduled_fallback_single_row(db_session, monkeypatch):
    """api/crawlers._run_scheduled_crawler 的 Celery 不可用分支：恰一行。"""
    monkeypatch.setattr(api_crawlers, "_celery_available", lambda: False)
    monkeypatch.setattr(api_crawlers, "is_allowed_crawler", lambda name: True)
    monkeypatch.setattr(api_crawlers.settings, "REDIS_URL", "")
    monkeypatch.setattr(api_crawlers, "SessionLocal", lambda: db_session)
    empty_section = dict(_SECTION, list_url="https://univ-test.edu.cn/zsgz/empty.htm")
    monkeypatch.setattr(api_crawlers, "get_crawler", lambda name: _patched_crawler_cls())
    monkeypatch.setattr(api_crawlers, "load_config", lambda name: _make_config([empty_section]))

    asyncio.run(api_crawlers._run_scheduled_crawler("official_announce"))

    rows = db_session.query(CrawlerRun).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.status == "success"
    assert row.started_at and row.finished_at
    assert row.duration_seconds >= 1


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """保险：即使误触限速也不引入真实等待（本文件网络全 mock）。"""
    monkeypatch.setattr("time.sleep", lambda s: None)
