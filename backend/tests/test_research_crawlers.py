"""外部调研 crawler 单元测试。

使用 mock 替代真实 HTTP 请求，覆盖 B站、网页文章、RSS 三个 crawler
以及 ResearchTransformer 的清洗/转换逻辑。
"""
import json
import tempfile
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.crawlers.research.bilibili_research_crawler import BilibiliResearchCrawler
from app.crawlers.research.rss_news_crawler import RssNewsCrawler
from app.crawlers.research.transformer import ResearchTransformer
from app.crawlers.research.web_article_crawler import WebArticleCrawler


# ======================================================================
# BilibiliResearchCrawler
# ======================================================================


class TestBilibiliResearchCrawler:
    def test_fetch_and_parse_returns_expected_fields(self):
        """mock B站搜索 API，验证 fetch/parse 输出字段。"""
        crawler = BilibiliResearchCrawler(
            config={"keyword": "408 计算机考研", "pages": 1}
        )

        search_response = MagicMock()
        search_response.json.return_value = {
            "code": 0,
            "data": {
                "result": [
                    {
                        "title": "<em class=\"keyword\">408</em> 计算机考研经验分享",
                        "bvid": "BV1Test1234",
                        "arcurl": "https://www.bilibili.com/video/BV1Test1234",
                        "description": "这是我的考研复习经验，包含数据结构和操作系统。",
                        "author": "考研学长",
                        "play": 12345,
                        "like": 678,
                        "tag": "考研,408,计算机",
                    }
                ]
            },
        }
        homepage_response = MagicMock()

        crawler._request = MagicMock(
            side_effect=[homepage_response, search_response]
        )

        raw = crawler.fetch()
        assert len(raw) == 1
        assert raw[0]["bvid"] == "BV1Test1234"

        parsed = crawler.parse(raw)
        assert len(parsed) == 1
        item = parsed[0]
        assert item["title"] == "408 计算机考研经验分享"
        assert item["bvid"] == "BV1Test1234"
        assert item["source_url"] == "https://www.bilibili.com/video/BV1Test1234"
        assert item["author"] == "考研学长"
        assert item["view_count"] == 12345
        assert item["like_count"] == 678
        assert item["tags"] == ["考研", "408", "计算机"]
        assert item["source_platform"] == "bilibili"
        assert item["category"] == "考研经验"

    def test_parse_strips_html_tags(self):
        """验证 HTML 标签清洗。"""
        crawler = BilibiliResearchCrawler(config={"keyword": "考研"})
        raw = [
            {
                "title": "<em class=\"keyword\">考研</em> <b>复试</b>经验",
                "bvid": "BVHtml",
                "description": "<p>这是正文</p>",
                "author": "作者",
                "play": "1000",
                "like": "50",
                "tag": "",
            }
        ]
        parsed = crawler.parse(raw)
        assert parsed[0]["title"] == "考研 复试经验"
        assert parsed[0]["content"] == "<p>这是正文</p>"

    def test_fetch_handles_api_error(self):
        """API 返回非 0 code 时统计错误并继续。"""
        crawler = BilibiliResearchCrawler(
            config={"keyword": "考研", "pages": 1}
        )
        error_response = MagicMock()
        error_response.json.return_value = {
            "code": -500,
            "message": "系统错误",
        }
        homepage_response = MagicMock()
        crawler._request = MagicMock(
            side_effect=[homepage_response, error_response]
        )

        raw = crawler.fetch()
        assert raw == []
        assert crawler.stats["errors"] == 1


# ======================================================================
# WebArticleCrawler
# ======================================================================


class TestWebArticleCrawler:
    def test_fetch_and_parse_extracts_title_content_source_url(self):
        """mock Jina Reader 返回文本，验证 title/content/source_url 提取。"""
        url = "https://example.com/kaoyan-guide"
        crawler = WebArticleCrawler(config={"urls": [url], "rate_limit": 0})

        jina_text = (
            "2025 计算机考研 408 复习指南\n"
            "\n"
            "第一轮复习建议从数据结构开始，然后是计算机组成原理。\n"
            "第二轮做真题，重点突破操作系统和计算机网络。\n"
        )

        with patch.object(
            crawler.session, "request", return_value=MagicMock(text=jina_text, raise_for_status=MagicMock())
        ) as mock_request:
            raw = crawler.fetch()

        assert len(raw) == 1
        assert raw[0]["url"] == url
        assert raw[0]["status"] == "ok"
        mock_request.assert_called_once()
        called_url = mock_request.call_args[0][1]
        assert called_url == f"https://r.jina.ai/{url}"

        parsed = crawler.parse(raw)
        assert len(parsed) == 1
        item = parsed[0]
        assert item["title"] == "2025 计算机考研 408 复习指南"
        assert item["source_url"] == url
        assert item["source_platform"] == "web"
        assert item["status"] == "ok"
        assert "第一轮复习建议" in item["content"]
        assert item["content"].startswith("2025 计算机考研 408 复习指南") is False

    def test_parse_failed_status(self):
        """抓取失败的条目应标记为 failed。"""
        crawler = WebArticleCrawler(config={"urls": []})
        raw = [
            {
                "url": "https://example.com/fail",
                "text": "",
                "status": "error",
                "error": "timeout",
            }
        ]
        parsed = crawler.parse(raw)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "https://example.com/fail"
        assert parsed[0]["content"] == ""
        assert parsed[0]["status"] == "failed"


# ======================================================================
# RssNewsCrawler
# ======================================================================


class TestRssNewsCrawler:
    def _make_feed_entry(self, **overrides):
        entry = MagicMock()
        entry.title = "教育部发布 2025 考研初试安排"
        entry.summary = "2025 年全国硕士研究生招生考试初试时间确定。"
        entry.description = "2025 年全国硕士研究生招生考试初试时间确定。"
        entry.content = [{"value": "详细内容：考试将于 2025 年 12 月举行。", "type": "text/html"}]
        entry.link = "https://example.com/news/1"
        entry.id = "https://example.com/news/1"
        entry.published_parsed = (2025, 9, 1, 10, 0, 0, 0, 0, 0)
        entry.updated_parsed = None
        entry.tags = [MagicMock(term="考研")]

        def _get(key, default=None):
            return getattr(entry, key, default)

        entry.get = _get
        for key, value in overrides.items():
            setattr(entry, key, value)
        return entry

    def test_parse_and_dedup(self, tmp_path):
        """mock feedparser.parse，验证 parse 结构和 store 去重。"""
        output_path = tmp_path / "rss_news_test.json"
        crawler = RssNewsCrawler(
            config={
                "feeds": ["https://example.com/feed.xml"],
                "output_path": str(output_path),
            }
        )

        feed_response = MagicMock()
        feed_response.content = b"<rss></rss>"
        crawler._request = MagicMock(return_value=feed_response)

        parsed_feed = MagicMock()
        parsed_feed.bozo = False
        parsed_feed.feed = {"title": "考研资讯"}
        entry1 = self._make_feed_entry()
        entry2 = self._make_feed_entry(
            title="另一所高校发布招生简章",
            link="https://example.com/news/2",
        )
        parsed_feed.entries = [entry1, entry2]

        with patch("app.crawlers.research.rss_news_crawler.feedparser.parse", return_value=parsed_feed):
            raw = crawler.fetch()

        assert len(raw) == 2
        assert raw[0]["_feed_title"] == "考研资讯"

        parsed = crawler.parse(raw)
        assert len(parsed) == 2
        assert parsed[0]["title"] == "教育部发布 2025 考研初试安排"
        assert parsed[0]["source_url"] == "https://example.com/news/1"
        assert parsed[0]["source_platform"] == "rss"
        assert parsed[0]["category"] == "考研资讯"
        assert "考研" in parsed[0]["tags"]

        # 第一次 store 应写入 2 条
        stored = crawler.store(parsed, db=None)
        assert stored == 2
        assert output_path.exists()

        # 再次 store 相同数据应去重
        stored2 = crawler.store(parsed, db=None)
        assert stored2 == 0
        assert crawler.stats["duplicates"] == 2

        with output_path.open("r", encoding="utf-8") as f:
            saved = json.load(f)
        assert len(saved) == 2

    def test_keyword_filter(self):
        """关键词过滤：未命中关键词的条目应被丢弃。"""
        crawler = RssNewsCrawler(
            config={"feeds": [], "keywords": ["计算机", "408"]}
        )
        items = [
            {"title": "计算机考研大纲发布", "summary": "包含 408 内容"},
            {"title": "教育新闻", "summary": "与考研无关"},
        ]
        assert crawler._matches_keywords(items[0]) is True
        assert crawler._matches_keywords(items[1]) is False


# ======================================================================
# ResearchTransformer
# ======================================================================


class TestResearchTransformer:
    def test_transform_bilibili_payload_structure(self):
        """验证 B站数据转换后的 ExperiencePost payload 结构。"""
        items = [
            {
                "title": "408 计算机考研上岸经验",
                "summary": "复习 408 的经验分享",
                "content": "我从数据结构开始复习，然后是操作系统。",
                "author": "学长 A",
                "bvid": "BV123",
                "source_url": "https://www.bilibili.com/video/BV123",
                "view_count": 5000,
                "like_count": 300,
                "tags": ["考研", "408"],
                "category": "考研经验",
                "source_platform": "bilibili",
            }
        ]
        payloads = ResearchTransformer.transform_bilibili(items)
        assert len(payloads) == 1
        payload = payloads[0]
        assert payload["title"] == "408 计算机考研上岸经验"
        assert payload["source_platform"] == "bilibili"
        assert payload["source_url"] == "https://www.bilibili.com/video/BV123"
        assert payload["external_view_count"] == 5000
        assert payload["external_like_count"] == 300
        assert "408" in payload["tags"]
        assert "数据结构" in payload["tags"]
        assert payload["status"] == "pending"
        assert payload["is_verified"] is False
        assert "user_id" in payload

    def test_transform_web_payload_structure(self):
        """验证网页文章数据转换后的 payload 结构。"""
        items = [
            {
                "title": "Title: 2025 考研数学复习规划",
                "content": "数学复习分为基础、强化、冲刺三个阶段。择校很关键。",
                "source_url": "https://example.com/math",
                "source_platform": "web",
                "status": "ok",
            }
        ]
        payloads = ResearchTransformer.transform_web(items)
        assert len(payloads) == 1
        payload = payloads[0]
        assert payload["title"] == "2025 考研数学复习规划"
        assert payload["source_platform"] == "web"
        assert payload["source_url"] == "https://example.com/math"
        assert "数学" in payload["tags"]
        assert "择校" in payload["tags"]
        assert payload["category"] == "复习"

    def test_transform_rss_payload_structure(self):
        """验证 RSS 数据转换后的 KaoyanNews payload 结构。"""
        now = datetime.now(timezone.utc).isoformat()
        items = [
            {
                "title": "高校发布复试通知",
                "summary": "多所高校公布复试安排",
                "content": "复试将于 3 月下旬开始，请考生关注官网。",
                "source_url": "https://example.com/retest",
                "published_at": "2025-03-01T08:00:00+00:00",
                "crawled_at": now,
                "category": "招生简章",
                "tags": ["复试"],
                "source_platform": "rss",
            }
        ]
        payloads = ResearchTransformer.transform_rss(items)
        assert len(payloads) == 1
        payload = payloads[0]
        assert payload["title"] == "高校发布复试通知"
        assert payload["source_platform"] == "rss"
        assert payload["category"] == "招生简章"
        assert isinstance(payload["published_at"], datetime)
        assert isinstance(payload["crawled_at"], datetime)
        assert "复试" in payload["tags"]

    def test_ad_filtering(self):
        """含广告关键词的内容应被过滤。"""
        items = [
            {
                "title": "考研资料分享加微信领取",
                "summary": "",
                "content": "加微信获取全部资料",
                "bvid": "BVAd",
                "source_url": "https://bilibili.com/video/BVAd",
                "view_count": 0,
                "like_count": 0,
                "tags": [],
                "source_platform": "bilibili",
            }
        ]
        assert ResearchTransformer.transform_bilibili(items) == []

    def test_tag_extraction(self):
        """验证学科与阶段标签抽取。"""
        text = "我考 408，重点复习数据结构和操作系统，正在准备复试。"
        tags = ResearchTransformer._extract_tags(text)
        assert "408" in tags
        assert "数据结构" in tags
        assert "操作系统" in tags
        assert "复试" in tags

    def test_dedup_by_url(self):
        """相同 source_url 的条目应去重。"""
        items = [
            {
                "title": "第一篇文章",
                "source_url": "https://example.com/a",
                "source_platform": "web",
            },
            {
                "title": "第二篇文章（重复链接）",
                "source_url": "https://example.com/a",
                "source_platform": "web",
            },
            {
                "title": "第三篇文章",
                "source_url": "https://example.com/b",
                "source_platform": "web",
            },
        ]
        payloads = ResearchTransformer.transform_web(items)
        assert len(payloads) == 2
        assert {p["source_url"] for p in payloads} == {
            "https://example.com/a",
            "https://example.com/b",
        }
