# backend/tests/test_bilibili_crawler.py
"""B站经验爬虫测试（Phase H：多关键词 + 分类细化 + 审核落库）。

不发起真实网络请求 —— mock crawler._request 返回构造的搜索 API 响应。
覆盖：
- 多关键词：config.keywords 列表 / 逗号分隔字符串解析，逐词抓取
- parse：标题去标签、播放/点赞数、bvid→source_url、简介兜底
- store：落 t_external_research_item + t_review_queue_item（PENDING 审核队列）
- 分类细化：transformer 心态/避坑 新分类
"""

import pytest
from sqlalchemy.orm import Session

from app.crawlers.research.bilibili_research_crawler import (
    DEFAULT_KEYWORDS,
    BilibiliResearchCrawler,
)
from app.crawlers.research.transformer import ResearchTransformer
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem


class _FakeResponse:
    """模拟 requests.Response：fetch 只调 .json()，无需完整对象。"""

    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _make_crawler(**config) -> BilibiliResearchCrawler:
    crawler = BilibiliResearchCrawler(config=config)
    return crawler


def _bili_api_payload(items: list[dict], code: int = 0) -> dict:
    return {"code": code, "message": "0", "data": {"result": items}}


class TestKeywords:
    def test_default_keywords_when_missing(self):
        c = _make_crawler()
        assert c.keywords == DEFAULT_KEYWORDS
        # 兼容旧字段：keyword = 第一个关键词
        assert c.keyword == DEFAULT_KEYWORDS[0]

    def test_keywords_list_config(self):
        c = _make_crawler(keywords=["考研数学", "考研英语"])
        assert c.keywords == ["考研数学", "考研英语"]
        assert c.keyword == "考研数学"

    def test_keywords_comma_string_config(self):
        c = _make_crawler(keywords="考研择校,考研复试经验")
        assert c.keywords == ["考研择校", "考研复试经验"]

    def test_blank_keywords_falls_back_to_default(self):
        c = _make_crawler(keywords=["", "  "])
        assert c.keywords == DEFAULT_KEYWORDS


class TestFetch:
    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch):
        """打桩随机 sleep（1-4s 控频），避免拖慢测试。"""
        monkeypatch.setattr(
            "app.crawlers.research.bilibili_research_crawler.time.sleep", lambda s: None
        )

    def test_fetch_iterates_keywords_and_pages(self, monkeypatch):
        """逐关键词逐页抓取，mock _request 不真网。"""
        c = _make_crawler(keywords=["考研数学", "考研英语"], pages=2)
        calls: list[str] = []

        def fake_request(url, method="GET", **kwargs):
            calls.append(url)
            return _FakeResponse(
                _bili_api_payload(
                    [{"title": f"<em>视频</em>{i}", "bvid": f"BV{i}"} for i in range(2)]
                )
            )

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()

        # 首页预热 1 次 + 2 关键词 × 2 页 = 5 次请求
        assert len(calls) == 5
        assert calls[0] == "https://www.bilibili.com"
        # 4 次 API 调用 × 每次 2 条 = 8 条视频结果
        assert len(raw) == 8
        assert "keyword=" in calls[1]

    def test_fetch_api_error_counts_and_continues(self, monkeypatch):
        c = _make_crawler(keywords=["考研数学"], pages=1)

        def fake_request(url, method="GET", **kwargs):
            if url == "https://www.bilibili.com":
                return _FakeResponse({"html": ""})
            return _FakeResponse(_bili_api_payload([], code=-412))

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        assert raw == []
        assert c.stats["errors"] >= 1

    def test_fetch_stops_when_page_empty(self, monkeypatch):
        """某页无结果 → 提前结束该关键词分页。"""
        c = _make_crawler(keywords=["考研数学"], pages=3)
        calls: list[str] = []

        def fake_request(url, method="GET", **kwargs):
            calls.append(url)
            if url == "https://www.bilibili.com":
                return _FakeResponse({"html": ""})
            # 第二次 API 请求（第 2 页）起返回空 → 提前结束
            api_calls = [u for u in calls if u.startswith("https://api.bilibili.com")]
            if len(api_calls) >= 2:
                return _FakeResponse(_bili_api_payload([]))
            return _FakeResponse(_bili_api_payload([{"title": "视频", "bvid": "BV1"}]))

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        assert len(raw) == 1


class TestParse:
    def test_parse_strips_html_title_and_counts(self):
        c = _make_crawler()
        parsed = c.parse(
            [
                {
                    "title": '<em class="keyword">考研数学</em>刷题经验',
                    "play": 12000,
                    "like": 356,
                    "bvid": "BV1xx411c7mD",
                    "description": "一战的数学复习规划与时间安排",
                    "author": "阿岳",
                    "tag": "考研,数学,经验",
                    "arcurl": "https://www.bilibili.com/video/BV1xx411c7mD",
                }
            ]
        )
        assert len(parsed) == 1
        item = parsed[0]
        assert item["title"] == "考研数学刷题经验"
        assert item["view_count"] == 12000
        assert item["like_count"] == 356
        assert item["source_url"] == "https://www.bilibili.com/video/BV1xx411c7mD"
        assert item["source_platform"] == "bilibili"
        assert "考研" in item["tags"]

    def test_parse_falls_back_to_bvid_url(self):
        """无 arcurl 时用 bvid 拼接外链。"""
        c = _make_crawler()
        parsed = c.parse([{"title": "复试经验", "bvid": "BV1abc", "play": 100}])
        assert parsed[0]["source_url"] == "https://www.bilibili.com/video/BV1abc"

    def test_parse_description_dash_fallback(self):
        """description 为 '-' 时用标题兜底。"""
        c = _make_crawler()
        parsed = c.parse([{"title": "心态调整", "description": "-", "bvid": "BV1x", "play": 1}])
        assert parsed[0]["content"] == "心态调整"
        assert parsed[0]["summary"] == "心态调整"


class TestStoreToReviewQueue:
    def test_store_creates_pending_queue_item(self, db_session: Session):
        """store → t_external_research_item + t_review_queue_item 均 PENDING。"""
        c = _make_crawler()
        items = c.parse(
            [
                {
                    "title": "408 考研避坑指南",
                    "description": "说说备考期间最后悔的几件事",
                    "bvid": "BV1zz",
                    "play": 800,
                    "like": 40,
                    "author": "UP主",
                    "tag": "考研",
                }
            ]
        )
        inserted = c.store(items, db=db_session)
        assert inserted == 1

        ext = (
            db_session.query(ExternalResearchItem)
            .filter(ExternalResearchItem.source_url == "https://www.bilibili.com/video/BV1zz")
            .first()
        )
        assert ext is not None
        assert ext.review_status == "PENDING"
        assert ext.item_type == "experience_post"
        assert ext.source_platform == "bilibili"

        queue = (
            db_session.query(ReviewQueueItem)
            .filter(ReviewQueueItem.source_url == "https://www.bilibili.com/video/BV1zz")
            .first()
        )
        assert queue is not None
        assert queue.review_status == "PENDING"

    def test_store_dedupes_same_url(self, db_session: Session):
        """同 URL 二次入库幂等（source_url 唯一索引）。"""
        c = _make_crawler()
        items = c.parse(
            [
                {
                    "title": "二战心态调整",
                    "description": "如何撑过疲惫期",
                    "bvid": "BV1dup",
                    "play": 5,
                }
            ]
        )
        assert c.store(items, db=db_session) == 1
        assert c.store(items, db=db_session) == 0
        ext_count = (
            db_session.query(ExternalResearchItem)
            .filter(ExternalResearchItem.source_url == "https://www.bilibili.com/video/BV1dup")
            .count()
        )
        assert ext_count == 1


class TestCategoryRefinement:
    """Phase H：transformer 分类细化（心态/避坑 前置）。"""

    def test_xintai_category(self):
        assert ResearchTransformer._infer_category("考研心态崩了怎么办") == "心态"
        assert ResearchTransformer._infer_category("二战很焦虑 想放弃") == "心态"

    def test_bikeng_category(self):
        assert ResearchTransformer._infer_category("考研避坑指南") == "避坑"
        assert ResearchTransformer._infer_category("过来人的教训：这些坑千万别踩") == "避坑"

    def test_legacy_categories_preserved(self):
        """旧分类（复试/调剂/择校/备考/复习）兼容保留。"""
        assert ResearchTransformer._infer_category("考研复试经验") == "复试"
        assert ResearchTransformer._infer_category("考研调剂信息") == "调剂"
        assert ResearchTransformer._infer_category("考研择校分析") == "择校"
        assert ResearchTransformer._infer_category("考研备考计划") == "备考"
        assert ResearchTransformer._infer_category("考研数学复习规划") == "复习"

    def test_unknown_falls_back_general(self):
        assert ResearchTransformer._infer_category("随便聊聊") == "general"
