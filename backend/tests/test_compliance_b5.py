# backend/tests/test_compliance_b5.py
"""B5 合规测试 — 真实数据导入状态断言 + 爬虫旁路收口断言。

覆盖（Phase B 数据合规化收口）：
- B3 导入脚本 dry-run：能从 real_data/ 真实文件解析出条目（条数 > 0、无解析错误）
- 入库状态：store_research_items 落库条目全为 PENDING
  （t_external_research_item + t_review_queue_item），同 URL 重复导入 0 新增（幂等）
- 旁路收口：白名单之外"已注册"爬虫 POST /api/crawlers/run、/schedules 一律 403；
  白名单内合规爬虫（yanzhao）正常放行
- 白名单自检：所有白名单源必须是已注册爬虫（防死名单、防名单与实际注册名不符）
"""

import json
import sys

import pytest

import app.crawlers.grad  # noqa: F401  — 触发 @register_crawler 注册真实爬虫
import app.crawlers.research  # noqa: F401
import scripts.import_real_data_to_queue as b3
from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES
from app.crawlers.registry import get_crawler
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem
from app.models.user import User
from app.services.research_ingestion import store_research_items


@pytest.fixture
def admin_headers(client, db_session):
    from app.core.security import hash_password

    admin = User(
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------- B3 导入脚本


def test_import_script_dry_run_parses_real_data(monkeypatch, capsys):
    """dry-run --json：真实数据可解析出条目，无单文件解析错误。

    该测试校验的是本地完整抓取快照的数据完整性；real_data 不在仓库内，
    CI/无数据环境下诚实跳过（web 组任一源文件存在才运行）。
    """
    web_files = {e[0] for e in b3.SOURCE_REGISTRY if e[2] == "web"}
    if not any((b3.REAL_DATA_DIR / f).exists() for f in web_files):
        pytest.skip("本地无 real_data 抓取快照（CI），数据完整性校验仅在数据就位时运行")
    monkeypatch.setattr(
        sys,
        "argv",
        ["import_real_data_to_queue.py", "--only", "web", "--limit", "5", "--json"],
    )
    b3.main()
    summary = json.loads(capsys.readouterr().out)

    assert summary["mode"] == "dry-run"
    assert summary["totals"]["web"] > 0, "web 组应能解析出至少 1 条真实数据"
    files = summary["files"]
    assert files, "应有文件被解析"
    assert all("error" not in info for info in files.values()), "任何文件都不应有解析错误"
    assert any(info["items"] > 0 for info in files.values())


def test_store_research_items_all_pending_and_idempotent(db_session):
    """B3 适配器产物 → store_research_items：全 PENDING 落库 + 同 URL 幂等。"""
    rows = b3._load_rows("bilibili_expand.json", None)[:5]
    items = b3._adapter_bilibili(rows)
    assert items, "真实 bilibili 数据应能适配出条目"
    assert all("source_url" in it for it in items)

    run_id = "b5" * 16  # CrawlerRun.id（UUID hex 32 位）
    kw = dict(
        crawler_name="bilibili_research",
        item_type="experience_post",
        items=items,
        source_platform="bilibili",
        run_id=run_id,
    )
    r1 = store_research_items(db_session, **kw)
    assert r1 == {"inserted": len(items), "duplicated": 0}

    for it in items:
        url = it["source_url"]
        ext = (
            db_session.query(ExternalResearchItem)
            .filter(ExternalResearchItem.source_url == url)
            .first()
        )
        assert ext is not None, "ExternalResearchItem 应存在"
        assert ext.review_status == "PENDING", "外部条目必须进审核队列（PENDING）"
        q = db_session.query(ReviewQueueItem).filter(ReviewQueueItem.source_url == url).first()
        assert q is not None, "ReviewQueueItem 应存在"
        assert q.review_status == "PENDING", "审核队列条目必须为 PENDING"

    # 幂等：同 URL 重复导入 → 0 新增，全部按重复跳过
    r2 = store_research_items(db_session, **kw)
    assert r2 == {"inserted": 0, "duplicated": len(items)}, "重复导入必须幂等"


# ---------------------------------------------------------------- 旁路收口


def test_run_endpoint_rejects_registered_non_whitelisted_crawler(client, admin_headers):
    """已注册但不在白名单的爬虫（mentor 直写业务表）→ /run 必须 403。

    注意：scoreline / scoreline_real / admission_ratio 三个假数据生成器
    已于 2026-09-02 注销注册，改用 mentor 作为非白注册爬虫代表。
    """
    assert get_crawler("mentor") is not None, "前置：mentor 已注册"
    assert "mentor" not in ALLOWED_CRAWLER_SOURCES

    resp = client.post(
        "/api/crawlers/run",
        headers=admin_headers,
        json={"source_name": "mentor"},
    )
    assert resp.status_code == 403
    assert "白名单" in resp.json()["detail"] or "合规" in resp.json()["detail"]


def test_run_endpoint_allows_whitelisted_crawler(client, admin_headers, monkeypatch):
    """合规爬虫（yanzhao，B1 改造后走 PENDING 队列）→ /run 正常放行。"""
    assert get_crawler("yanzhao") is not None
    assert "yanzhao" in ALLOWED_CRAWLER_SOURCES

    # 模拟 Celery 投递成功，避免测试里真实执行爬虫（网络/DB 副作用）
    monkeypatch.setattr("app.api.crawlers._dispatch_crawler_task", lambda *a, **k: True)
    resp = client.post(
        "/api/crawlers/run",
        headers=admin_headers,
        json={"source_name": "yanzhao"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    assert resp.json()["task_id"]


def test_schedules_rejects_registered_non_whitelisted_crawler(
    client,
    admin_headers,
    monkeypatch,
):
    """定时任务创建同样受白名单护栏约束：非白名单爬虫 → 403。"""
    from types import SimpleNamespace

    monkeypatch.setattr(
        "app.api.crawlers.get_scheduler",
        lambda: SimpleNamespace(add_job=lambda *a, **k: None, get_job=lambda *a, **k: None),
    )
    resp = client.post(
        "/api/crawlers/schedules",
        headers=admin_headers,
        json={"source_name": "mentor", "cron": "0 * * * *"},
    )
    assert resp.status_code == 403
    assert "白名单" in resp.json()["detail"] or "合规" in resp.json()["detail"]


def test_whitelist_entries_all_registered():
    """白名单自检：每个允许源都必须是已注册爬虫，防止死名单 / 名实不符。

    曾出现：白名单写 "rss_news_crawler"（模块文件名），实际注册名
    "rss_news_research" — 导致合规 RSS 爬虫被护栏误杀。
    """
    unregistered = [n for n in ALLOWED_CRAWLER_SOURCES if get_crawler(n) is None]
    assert unregistered == [], f"白名单含未注册爬虫: {unregistered}"
    assert "rss_news_research" in ALLOWED_CRAWLER_SOURCES
    assert "rss_news_crawler" not in ALLOWED_CRAWLER_SOURCES
