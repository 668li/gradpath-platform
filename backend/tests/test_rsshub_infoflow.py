"""RSSHub 资讯流路由（杠杆 #5）单元测试。

覆盖：资讯流路由入白名单、分类映射、白名单校验放行/拒绝、
fetch 对知乎日报路由的解析（mock _request，不碰真实网络）。
"""

from unittest.mock import MagicMock

from app.crawlers.research.rsshub_research_crawler import DEFAULT_ROUTES, RSSHubCrawler

ZHIHU_DAILY_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>知乎日报</title><link>https://daily.zhihu.com</link><description>知乎日报</description>
<item>
<title><![CDATA[考研人如何规划全年复习时间线？]]></title>
<link>https://zhuanlan.zhihu.com/p/12345678</link>
<description><![CDATA[<p>本文从三月初到考前，按月拆解复习节奏。</p><p>全文共 800 字。</p>]]></description>
<guid>https://zhuanlan.zhihu.com/p/12345678</guid>
<pubDate>Sat, 16 Aug 2026 08:00:00 GMT</pubDate>
</item>
<item>
<title><![CDATA[应届生第一份工作怎么选城市？]]></title>
<link>https://zhuanlan.zhihu.com/p/87654321</link>
<description><![CDATA[<p>城市选择决定职业天花板。</p>]]></description>
<guid>https://zhuanlan.zhihu.com/p/87654321</guid>
<pubDate>Sat, 16 Aug 2026 07:00:00 GMT</pubDate>
</item>
</channel></rss>""".encode()


class TestInfoFlowRoutes:
    def test_infoflow_routes_in_default_routes(self):
        """杠杆 #5 资讯流路由必须入硬编码白名单（否则采集器直接跳过）。"""
        for route in ("zhihu/daily", "zhihu/pin/hotlist"):
            assert route in DEFAULT_ROUTES

    def test_validate_allows_infoflow_routes(self):
        crawler = RSSHubCrawler()
        for route in ("zhihu/daily", "zhihu/pin/hotlist"):
            ok, _ = crawler._validate_outbound_url(f"http://127.0.0.1:1200/{route}?limit=15")
            assert ok is True

    def test_validate_rejects_non_whitelisted_route(self):
        crawler = RSSHubCrawler()
        ok, msg = crawler._validate_outbound_url("http://127.0.0.1:1200/zhihu/secret?limit=15")
        assert ok is False
        assert "白名单" in msg


class TestCategoryMapping:
    def test_infoflow_category(self):
        """资讯流路由 → 资讯·前缀分类；研招路由保持原格式。"""
        crawler = RSSHubCrawler()
        assert crawler._category_for("zhihu/daily", "知乎日报") == "资讯·知乎日报"
        assert crawler._category_for("zhihu/pin/hotlist", "知乎想法热榜") == "资讯·知乎热榜"
        assert crawler._category_for("hust/yjs", "华中科技大学研究生院").startswith("研招公告·")


class TestFetchParse:
    def _make_crawler(self, route):
        crawler = RSSHubCrawler(config={"routes": [route]})
        mock_resp = MagicMock()
        mock_resp.content = ZHIHU_DAILY_RSS
        return crawler, mock_resp

    def test_fetch_zhihu_daily(self, monkeypatch):
        crawler, mock_resp = self._make_crawler("zhihu/daily")
        monkeypatch.setattr(crawler, "_request", lambda url: mock_resp)
        raw = crawler.fetch()
        assert len(raw) == 2
        assert all(r["_route"] == "zhihu/daily" for r in raw)

    def test_parse_strips_html_and_truncates(self, monkeypatch):
        crawler, mock_resp = self._make_crawler("zhihu/daily")
        monkeypatch.setattr(crawler, "_request", lambda url: mock_resp)
        raw = crawler.fetch()
        parsed = crawler.parse(raw)
        assert len(parsed) == 2
        item = parsed[0]
        assert item["category"] == "资讯·知乎日报"
        assert item["source_platform"] == "rsshub"
        assert item["status"] == "pending"
        assert item["title"] == "考研人如何规划全年复习时间线？"
        assert item["source_url"] == "https://zhuanlan.zhihu.com/p/12345678"
        # HTML 剥离 + 截断 500（对齐 transform_rss 语义）
        assert "<p>" not in item["summary"]
        assert len(item["summary"]) <= 500
        assert item["published_at"] is not None

    def test_skip_missing_source_url(self, monkeypatch):
        rss = ZHIHU_DAILY_RSS.replace(b"https://zhuanlan.zhihu.com/p/12345678", b"")
        crawler = RSSHubCrawler(config={"routes": ["zhihu/daily"]})
        mock_resp = MagicMock()
        mock_resp.content = rss
        monkeypatch.setattr(crawler, "_request", lambda url: mock_resp)
        parsed = crawler.parse(crawler.fetch())
        assert len(parsed) == 1
