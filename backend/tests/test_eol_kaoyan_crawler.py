# backend/tests/test_eol_kaoyan_crawler.py
"""中国教育在线考研频道爬虫（Phase B1）测试 — mock 网络层验证解析与入库。

覆盖：
- fetch：列表页解析（标题/链接/日期），fetch_detail=False 时跳过详情
- fetch + 详情页：TRS_Editor 正文提取
- parse：transform_rss 输出标准 payload（含 quality_score/quality_grade 注入）
- store：mock 采集产物 → ExternalResearchItem + ReviewQueueItem 入 PENDING 队列
"""

from app.crawlers.research.eol_kaoyan_crawler import (
    DEFAULT_LIST_URL,
    EolKaoyanCrawler,
    _extract_detail_body,
    _parse_date,
)
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem

LIST_PAGE = """
<html><body>
<div class="fline"><a href="news/20260815/1.shtml">2026考研报名时间公布</a></div>
<div class="sline"><a href="news/20260815/1.shtml">查看详情</a></div>
<div class="tline"><span class="time">2026-08-15</span></div>

<div class="fline"><a href="news/20260814/2.shtml">某大学2026年招生简章发布</a></div>
<div class="sline"><a href="news/20260814/2.shtml">查看详情</a></div>
<div class="tline"><span class="time">2026年08月14日</span></div>
</body></html>
"""

DETAIL_PAGE = """
<html><body>
<div class="TRS_Editor">
  <p>网上报名时间为2025年10月15日至10月28日，</p>
  <p>初试时间为2025年12月20日。</p>
</div>
</body></html>
"""


class _FakeResponse:
    """最小响应替身：携带 text/encoding，兼容 _request 返回值用法。"""

    def __init__(self, text: str):
        self.text = text
        self.encoding = "utf-8"


class TestExtractHelpers:
    def test_extract_detail_body_strips_tags(self):
        text = _extract_detail_body(DETAIL_PAGE)
        assert "网上报名时间为2025年10月15日至10月28日" in text
        assert "初试时间为2025年12月20日" in text
        assert "<p>" not in text

    def test_extract_detail_body_missing_returns_empty(self):
        assert _extract_detail_body("<html>无正文容器</html>") == ""

    def test_parse_date_formats(self):
        assert _parse_date("2026-08-15") is not None
        assert _parse_date("2026年08月14日") is not None
        assert _parse_date("not-a-date") is None
        assert _parse_date("") is None


class TestFetch:
    def test_fetch_list_only_no_detail(self, monkeypatch):
        """fetch_detail=False（--no-detail）：仅列表信息，不发详情请求。"""
        requested: list[str] = []

        # monkeypatch 挂在类上 → 未绑定，需接收 self 参数
        def fake_request(self, url, method="GET", **kw):
            requested.append(url)
            return _FakeResponse(LIST_PAGE)

        monkeypatch.setattr(EolKaoyanCrawler, "_request", fake_request)
        crawler = EolKaoyanCrawler(config={"fetch_detail": False, "rate_limit": 0})

        items = crawler.fetch()
        assert len(items) == 2
        first = items[0]
        assert first["title"] == "2026考研报名时间公布"
        assert first["url"].startswith("https://") and "1.shtml" in first["url"]
        assert first["published_at"] is not None
        assert first["detail_text"] == ""
        # 只请求了列表页，未请求详情
        assert requested == [crawler.list_url]

    def test_fetch_with_detail_extracts_body(self, monkeypatch):
        """fetch_detail=True：逐条抓详情正文（列表页 + 2 个详情页）。"""
        pages = {
            DEFAULT_LIST_URL: LIST_PAGE,
            "https://kaoyan.eol.cn/nnews/news/20260815/1.shtml": DETAIL_PAGE,
            "https://kaoyan.eol.cn/nnews/news/20260814/2.shtml": DETAIL_PAGE,
        }

        def fake_request(self, url, method="GET", **kw):
            return _FakeResponse(pages.get(url, "<html></html>"))

        monkeypatch.setattr(EolKaoyanCrawler, "_request", fake_request)
        crawler = EolKaoyanCrawler(config={"fetch_detail": True, "rate_limit": 0})

        items = crawler.fetch()
        assert len(items) == 2
        assert "报名时间为2025年10月15日" in items[0]["detail_text"]

    def test_detail_failure_degrades_to_empty(self, monkeypatch):
        """详情抓取失败降级为空串，条目仍保留（标题入库）。"""

        def fake_request(self, url, method="GET", **kw):
            if url == DEFAULT_LIST_URL:
                return _FakeResponse(LIST_PAGE)
            raise RuntimeError("网络不可用")

        monkeypatch.setattr(EolKaoyanCrawler, "_request", fake_request)
        crawler = EolKaoyanCrawler(config={"fetch_detail": True, "rate_limit": 0})

        items = crawler.fetch()
        assert len(items) == 2
        assert all(i["detail_text"] == "" for i in items)


class TestParse:
    def test_parse_injects_standard_payload(self, monkeypatch):
        monkeypatch.setattr(EolKaoyanCrawler, "_request", lambda *a, **kw: _FakeResponse(""))
        crawler = EolKaoyanCrawler(config={"fetch_detail": False, "rate_limit": 0})

        raw = [
            {
                "title": "2026考研报名时间公布",
                "url": "https://kaoyan.eol.cn/nnews/news/20260815/1.shtml",
                "published_at": _parse_date("2026-08-15"),
                "detail_text": "",
            }
        ]
        parsed = crawler.parse(raw)
        assert len(parsed) == 1
        item = parsed[0]
        # transform_rss 标准字段
        assert item["title"] == "2026考研报名时间公布"
        assert item["source_url"].startswith("http")
        assert item["source_platform"] == "eol"
        assert item["category"] != "general"
        assert isinstance(item["summary"], str) and item["summary"]
        # 质量分注入（入库过滤消费）
        assert 0 <= item["quality_score"] <= 100
        assert item["quality_grade"] in {"A", "B", "C", "D"}


class TestStore:
    def test_store_creates_pending_queue_items(self, db_session):
        """store 走 store_research_items：外部条目 + 审核队列（PENDING）。"""
        crawler = EolKaoyanCrawler(config={"fetch_detail": False, "rate_limit": 0})
        items = [
            {
                "title": "2026考研报名时间公布",
                "summary": "网上报名 10 月 15 日启动",
                "content": "网上报名时间为2025年10月15日至10月28日。",
                "source_url": "https://kaoyan.eol.cn/nnews/news/20260815/1.shtml",
                "published_at": "2026-08-15T00:00:00Z",
                "crawled_at": "2026-08-15T08:00:00Z",
                "category": "考研快讯",
                "tags": [],
                "source_platform": "eol",
                "quality_score": 80,
                "quality_grade": "A",
            }
        ]

        inserted = crawler.store(items, db=db_session)
        assert inserted == 1

        ext = (
            db_session.query(ExternalResearchItem)
            .filter(ExternalResearchItem.source_url == items[0]["source_url"])
            .first()
        )
        assert ext is not None
        assert ext.item_type == "kaoyan_news"
        assert ext.crawler_name == "eol_kaoyan"

        queue = (
            db_session.query(ReviewQueueItem).filter(ReviewQueueItem.ref_item_id == ext.id).first()
        )
        assert queue is not None
        assert queue.review_status == "PENDING"

    def test_store_accepts_datetime_meta(self, db_session):
        """transform_rss 产物携带 datetime（published_at/crawled_at）→ external_meta 可 JSON 序列化。

        回归：真实采集曾因 datetime 写入 JSONB 抛 TypeError，store 前需转 isoformat。
        """
        from datetime import datetime, timezone

        crawler = EolKaoyanCrawler(config={"fetch_detail": False, "rate_limit": 0})
        items = [
            {
                "title": "2026考研复试线公布",
                "summary": "复试线公布",
                "content": "各院校陆续公布复试分数线，请关注报考院校官网。",
                "source_url": "https://kaoyan.eol.cn/nnews/news/20260816/3.shtml",
                "published_at": datetime(2026, 8, 16, tzinfo=timezone.utc),
                "crawled_at": datetime(2026, 8, 16, 8, 0, tzinfo=timezone.utc),
                "category": "考研快讯",
                "tags": [],
                "source_platform": "eol",
                "quality_score": 80,
                "quality_grade": "A",
            }
        ]

        assert crawler.store(items, db=db_session) == 1
        ext = (
            db_session.query(ExternalResearchItem)
            .filter(ExternalResearchItem.source_url == items[0]["source_url"])
            .first()
        )
        assert ext is not None
        # JSONB 落库成功且时间已转 isoformat 字符串（可 JSON 序列化）
        assert ext.external_meta["published_at"] == "2026-08-16T00:00:00+00:00"
        assert ext.external_meta["crawled_at"] == "2026-08-16T08:00:00+00:00"

    def test_store_dedups_same_url(self, db_session):
        """同 source_url 二次入库 → duplicated，不新增。"""
        crawler = EolKaoyanCrawler(config={"fetch_detail": False, "rate_limit": 0})
        item = {
            "title": "某大学2026年招生简章",
            "summary": "招生简章",
            "content": "2026 年硕士研究生招生简章发布。",
            "source_url": "https://kaoyan.eol.cn/nnews/news/20260814/2.shtml",
            "published_at": "2026-08-14T00:00:00Z",
            "crawled_at": "2026-08-15T08:00:00Z",
            "category": "考研快讯",
            "tags": [],
            "source_platform": "eol",
        }
        assert crawler.store([item], db=db_session) == 1
        # 二次入库：URL 唯一约束 → 去重
        assert crawler.store([item], db=db_session) == 0
