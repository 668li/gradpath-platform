"""Celery worker 侧白名单复查回归 — 对抗审计 F3 修复（2026-09-06）。

白名单原本只在 API/APScheduler/CLI 三入口检查；worker 是最后一道关，
本文件锁死：
- run_crawler_task 直投非白名单名 → failed 拒绝，爬虫类绝不被实例化
- run_scheduled_crawler_task 同样拒
- 对照组：白名单名照常通过守卫走原执行路径（守卫不是全量误杀）
"""

from types import SimpleNamespace
from uuid import uuid4

from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES
from app.tasks import crawler_tasks

_GUARD_ERROR_MARK = "不在准入白名单"  # 守卫专属报错串；任务外层有 catch-all，
# 断言必须精确匹配守卫报错，否则 get_crawler 崩溃返回的 failed 会伪装成守卫生效


def _boom_get_crawler(monkeypatch):
    def _boom(name):
        raise AssertionError(f"REGISTRY-REACHED:{name}")

    monkeypatch.setattr(crawler_tasks, "get_crawler", _boom)


def _silence_side_channels(monkeypatch):
    monkeypatch.setattr(
        crawler_tasks,
        "ws_manager",
        SimpleNamespace(notify_task_sync=lambda *a, **k: None, broadcast_sync=lambda p: None),
    )


def test_premise_mentor_not_whitelisted():
    assert "mentor" not in ALLOWED_CRAWLER_SOURCES


def test_user_task_rejects_non_whitelisted(monkeypatch):
    _boom_get_crawler(monkeypatch)
    _silence_side_channels(monkeypatch)
    result = crawler_tasks.run_crawler_task.run(uuid4().hex[:12], "mentor", False)
    assert result["status"] == "failed"
    assert _GUARD_ERROR_MARK in result["error"]
    assert "REGISTRY-REACHED" not in result["error"]  # 未越界到 get_crawler


def test_scheduled_task_rejects_non_whitelisted(monkeypatch):
    _boom_get_crawler(monkeypatch)
    result = crawler_tasks.run_scheduled_crawler_task.run("mentor")
    assert result["status"] == "failed"
    assert _GUARD_ERROR_MARK in result["error"]
    assert "REGISTRY-REACHED" not in result["error"]  # 未越界到 get_crawler


def test_whitelisted_name_still_executes(monkeypatch, db_session):
    """对照组：白名单名 eol_kaoyan 不被新守卫拦截，照常进入执行路径。"""

    class _FakeCrawler:
        category = "research"

        def __init__(self, config=None):
            self.config = config

        def run(self, db=None):
            return {"status": "ok", "fetched": 0, "stored": 0}

    monkeypatch.setattr(crawler_tasks, "get_crawler", lambda name: _FakeCrawler)
    monkeypatch.setattr(crawler_tasks, "load_config", lambda name: {})
    monkeypatch.setattr(crawler_tasks, "SessionLocal", lambda: db_session)
    _silence_side_channels(monkeypatch)

    result = crawler_tasks.run_crawler_task.run(uuid4().hex[:12], "eol_kaoyan", False)
    assert result["status"] == "ok"
