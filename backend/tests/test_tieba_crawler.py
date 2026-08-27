# backend/tests/test_tieba_crawler.py
"""百度贴吧避坑帖爬虫测试（Phase I）。

不发起真实网络请求 —— mock crawler._request 返回构造的 HTML。
覆盖：
- fetch：列表页按避坑关键词过滤标题 → 抓帖子首页正文；max_items 截断
- robots 不允许 → fail-safe：0 条结果，错误计数如实记录
- parse：标题/首楼正文提取、登录墙标记丢弃、抓取失败诚实记录
- store：落 t_external_research_item + t_review_queue_item（PENDING 审核队列）
"""

import pytest

from app.crawlers.research.tieba_research_crawler import (
    DEFAULT_KEYWORDS,
    TiebaResearchCrawler,
    patch_href,
)
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem

_LIST_HTML = """
<html><body>
<a href="/p/1001" class="j_th_tit ">考研避坑：这些学校慎报</a>
<a href="/p/1002" class="j_th_tit ">二战教训：别把时间浪费在无效刷题</a>
<a href="/p/1003" class="j_th_tit ">数学经验分享</a>
<a href="/p/1004" class="j_th_tit ">劝退：双非调剂实录</a>
</body></html>
"""

_THREAD_HTML = """
<html><body>
<h1 class="core_title_txt ">考研避坑：这些学校慎报</h1>
<div class="d_post_content ">千万不要报那些压分院校，我去年就是被压分调剂失败的。<br>真题一定要吃透。</div>
</body></html>
"""

_LOGIN_WALL_HTML = """
<html><body>
<h1 class="core_title_txt ">考研避坑帖</h1>
<div class="d_post_content ">请先登录后查看完整内容</div>
</body></html>
"""


class _FakeResponse:
    """模拟 requests.Response：fetch 只调 .text。"""

    def __init__(self, text: str):
        self.text = text


def _make_crawler(**config) -> TiebaResearchCrawler:
    return TiebaResearchCrawler(config=config)


class TestConfig:
    def test_default_forum_and_keywords(self):
        c = _make_crawler()
        assert c.forum == "考研"
        assert c.keywords == DEFAULT_KEYWORDS

    def test_custom_forum_and_keywords(self):
        c = _make_crawler(forum="计算机考研", keywords="避坑,教训")
        assert c.forum == "计算机考研"
        assert c.keywords == ["避坑", "教训"]

    def test_patch_href_strips_query(self):
        assert patch_href("/p/12345?pn=0") == "/p/12345"
        assert patch_href("/p/12345") == "/p/12345"


class TestFetch:
    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch):
        monkeypatch.setattr(
            "app.crawlers.research.tieba_research_crawler.time.sleep", lambda s: None
        )

    def test_fetch_filters_by_keyword_and_fetches_threads(self, monkeypatch):
        c = _make_crawler(max_items=0)
        calls: list[str] = []

        def fake_request(url, method="GET", **kwargs):
            calls.append(url)
            if url.startswith("https://tieba.baidu.com/f?"):
                return _FakeResponse(_LIST_HTML)
            return _FakeResponse(_THREAD_HTML)

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        # 列表页 1 次 + 3 篇避坑帖（"数学经验分享" 不含关键词被过滤）
        assert len(calls) == 1 + 3
        assert calls[0].startswith("https://tieba.baidu.com/f?kw=%E8%80%83%E7%A0%94")
        assert len(raw) == 3
        assert all(r["status"] == "ok" for r in raw)
        titles = [r["title_hint"] for r in raw]
        assert "数学经验分享" not in titles
        assert any("慎报" in t for t in titles)

    def test_fetch_max_items_truncates(self, monkeypatch):
        c = _make_crawler(max_items=2)

        def fake_request(url, method="GET", **kwargs):
            if url.startswith("https://tieba.baidu.com/f?"):
                return _FakeResponse(_LIST_HTML)
            return _FakeResponse(_THREAD_HTML)

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        assert len(raw) == 2  # 达到 max_items 提前停止

    def test_robots_denied_yields_zero_results(self, monkeypatch):
        """列表页 robots 不允许 → 0 条结果 + 错误计数如实记录。"""
        c = _make_crawler()
        monkeypatch.setattr(c, "_validate_outbound_url", lambda url: (True, ""))
        monkeypatch.setattr(c, "_check_robots_allowed", lambda url: False)
        raw = c.fetch()
        assert raw == []
        assert c.stats["errors"] >= 1

    def test_list_page_failure_continues_honestly(self, monkeypatch):
        c = _make_crawler(pages=2)

        def fake_request(url, method="GET", **kwargs):
            raise RuntimeError("超时")

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        assert raw == []
        assert c.stats["errors"] == 2  # 两页都失败，如实计数


class TestParse:
    def test_extracts_title_and_first_floor(self):
        c = _make_crawler()
        parsed = c.parse(
            [
                {
                    "url": "https://tieba.baidu.com/p/1001",
                    "html": _THREAD_HTML,
                    "title_hint": "考研避坑：这些学校慎报",
                    "status": "ok",
                }
            ]
        )
        assert len(parsed) == 1
        item = parsed[0]
        assert item["title"] == "考研避坑：这些学校慎报"
        assert "压分院校" in item["content"]
        assert "真题" in item["content"]
        assert item["source_platform"] == "tieba"
        assert item["status"] == "ok"

    def test_login_wall_dropped(self):
        c = _make_crawler()
        parsed = c.parse(
            [{"url": "https://tieba.baidu.com/p/1", "html": _LOGIN_WALL_HTML, "status": "ok"}]
        )
        assert parsed[0]["status"] == "failed"
        assert parsed[0]["content"] == ""
        assert "登录墙" in parsed[0]["error"]

    def test_fetch_error_item_kept_honestly(self):
        c = _make_crawler()
        parsed = c.parse(
            [
                {
                    "url": "https://tieba.baidu.com/p/1",
                    "html": "",
                    "title_hint": "考研避坑",
                    "status": "error",
                    "error": "robots.txt 不允许抓取",
                }
            ]
        )
        assert parsed[0]["status"] == "failed"
        assert "robots.txt 不允许抓取" in parsed[0]["error"]
        assert parsed[0]["title"] == "考研避坑"  # 用列表页标题提示兜底


class TestStoreToReviewQueue:
    def test_store_creates_pending_queue_item(self, db_session):
        c = _make_crawler()
        items = c.parse(
            [
                {
                    "url": "https://tieba.baidu.com/p/7001",
                    "html": _THREAD_HTML,
                    "title_hint": "考研避坑：这些学校慎报",
                    "status": "ok",
                }
            ]
        )
        inserted = c.store(items, db=db_session)
        assert inserted == 1

        ext = (
            db_session.query(ExternalResearchItem)
            .filter(ExternalResearchItem.source_url == "https://tieba.baidu.com/p/7001")
            .first()
        )
        assert ext is not None
        assert ext.review_status == "PENDING"
        assert ext.item_type == "experience_post"
        assert ext.source_platform == "tieba"
        assert ext.crawler_name == "tieba_research"

        queue = (
            db_session.query(ReviewQueueItem)
            .filter(ReviewQueueItem.source_url == "https://tieba.baidu.com/p/7001")
            .first()
        )
        assert queue is not None
        assert queue.review_status == "PENDING"

    def test_store_dedupes_same_url(self, db_session):
        c = _make_crawler()
        items = c.parse(
            [
                {
                    "url": "https://tieba.baidu.com/p/7002",
                    "html": _THREAD_HTML,
                    "title_hint": "考研避坑",
                    "status": "ok",
                }
            ]
        )
        assert c.store(items, db=db_session) == 1
        assert c.store(items, db=db_session) == 0
