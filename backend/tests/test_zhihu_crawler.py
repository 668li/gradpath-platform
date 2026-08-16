# backend/tests/test_zhihu_crawler.py
"""知乎公开专栏爬虫测试（Phase I）。

不发起真实网络请求 —— mock crawler._request 返回构造的 HTML。
覆盖：
- fetch：文章 URL / 专栏归档页 /p/ 链接解析、去重、max_pages 截断
- robots 不允许 → fail-safe：0 条成功结果，如实记录失败原因
- parse：标题/正文提取、正文内 script/style 剔除、登录墙/验证码标记丢弃
- store：落 t_external_research_item + t_review_queue_item（PENDING 审核队列）
"""
import pytest

from app.crawlers.research.zhihu_research_crawler import ZhihuResearchCrawler
from app.models.ingestion import ExternalResearchItem, ReviewQueueItem

_ARTICLE_HTML = """
<html><head><title>2026 考研 408 一战上岸经验 - 知乎</title></head>
<body>
<div class="Post-Header"><h1 class="Post-Title">408 计算机考研一战上岸经验</h1></div>
<div class="Post-RichTextContainer">
  <p>我本科双非，一战考了 380 分上岸某 985。</p>
  <p>每天刷 4 小时真题，错题整理成笔记反复复盘。</p>
  <div><ul><li>不要迷信网课时长</li></ul></div>
  <script>var secret = "不该出现";</script>
  <style>.noise { display: none; }</style>
</div>
<div class="Post-footer">赞同 123 · 评论 45 · 分享</div>
</body></html>
"""

_ARCHIVE_HTML = """
<html><body>
<a href="//zhuanlan.zhihu.com/p/11111">第一篇文章</a>
<a href="https://zhuanlan.zhihu.com/p/22222">第二篇文章</a>
<a href="https://zhuanlan.zhihu.com/p/11111">重复链接</a>
<a href="https://www.zhihu.com/question/333">不是文章</a>
</body></html>
"""

_LOGIN_WALL_HTML = """
<html><head><title>需要登录 - 知乎</title></head>
<body>
<div class="Post-RichTextContainer"><p>登录后查看全文，请先登录知乎账号</p></div>
</body></html>
"""


class _FakeResponse:
    """模拟 requests.Response：fetch 只调 .text。"""

    def __init__(self, text: str):
        self.text = text


def _make_crawler(**config) -> ZhihuResearchCrawler:
    return ZhihuResearchCrawler(config=config)


class TestFetch:
    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch):
        """打桩随机 sleep（1-3s 控频），避免拖慢测试。"""
        monkeypatch.setattr(
            "app.crawlers.research.zhihu_research_crawler.time.sleep", lambda s: None
        )

    def test_fetch_article_urls(self, monkeypatch):
        c = _make_crawler(seed_urls=["https://zhuanlan.zhihu.com/p/12345"])
        calls: list[str] = []

        def fake_request(url, method="GET", **kwargs):
            calls.append(url)
            return _FakeResponse(_ARTICLE_HTML)

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        assert calls == ["https://zhuanlan.zhihu.com/p/12345"]
        assert len(raw) == 1
        assert raw[0]["status"] == "ok"

    def test_fetch_archive_page_resolves_article_links(self, monkeypatch):
        """归档页 → 解析 /p/ 链接去重后逐篇抓取。"""
        c = _make_crawler(seed_urls=["https://www.zhihu.com/column/c_test"])
        calls: list[str] = []

        def fake_request(url, method="GET", **kwargs):
            calls.append(url)
            if url == "https://www.zhihu.com/column/c_test":
                return _FakeResponse(_ARCHIVE_HTML)
            return _FakeResponse(_ARTICLE_HTML)

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        # 归档页 1 次 + 去重后 2 篇文章
        assert calls == [
            "https://www.zhihu.com/column/c_test",
            "https://zhuanlan.zhihu.com/p/11111",
            "https://zhuanlan.zhihu.com/p/22222",
        ]
        assert len(raw) == 2
        assert {r["url"] for r in raw} == {
            "https://zhuanlan.zhihu.com/p/11111",
            "https://zhuanlan.zhihu.com/p/22222",
        }

    def test_fetch_archive_page_max_pages_truncates(self, monkeypatch):
        c = _make_crawler(seed_urls=["https://www.zhihu.com/column/c_test"], max_pages=1)
        calls: list[str] = []

        def fake_request(url, method="GET", **kwargs):
            calls.append(url)
            if url == "https://www.zhihu.com/column/c_test":
                return _FakeResponse(_ARCHIVE_HTML)
            return _FakeResponse(_ARTICLE_HTML)

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        assert len(raw) == 1

    def test_robots_denied_yields_zero_ok_results(self, monkeypatch):
        """robots 不允许 → fail-safe：抓取 0 条成功结果，失败原因如实记录。"""
        c = _make_crawler(seed_urls=["https://zhuanlan.zhihu.com/p/12345"])
        # 校验通过但 robots 明确禁止 → _request 抛异常，fetch 如实记录
        monkeypatch.setattr(c, "_validate_outbound_url", lambda url: (True, ""))
        monkeypatch.setattr(c, "_check_robots_allowed", lambda url: False)
        raw = c.fetch()
        assert len(raw) == 1
        assert raw[0]["status"] == "error"
        assert "robots.txt 不允许抓取" in raw[0]["error"]
        # parse 后 0 条成功结果（诚实，不编造）
        parsed = c.parse(raw)
        assert parsed[0]["status"] == "failed"
        assert parsed[0]["content"] == ""

    def test_archive_fetch_failure_honest_empty(self, monkeypatch):
        c = _make_crawler(seed_urls=["https://www.zhihu.com/column/c_test"])

        def fake_request(url, method="GET", **kwargs):
            raise RuntimeError("连接被拒")

        monkeypatch.setattr(c, "_request", fake_request)
        raw = c.fetch()
        assert raw == []  # 归档页失败 → 无文章链接，如实 0 条


class TestParse:
    def test_extracts_title_and_content(self):
        c = _make_crawler()
        parsed = c.parse([{"url": "https://zhuanlan.zhihu.com/p/1", "html": _ARTICLE_HTML, "status": "ok"}])
        assert len(parsed) == 1
        item = parsed[0]
        assert item["title"] == "408 计算机考研一战上岸经验"
        assert "380 分" in item["content"]
        assert "错题" in item["content"]
        assert item["source_platform"] == "zhihu"
        assert item["status"] == "ok"

    def test_script_style_excluded_from_content(self):
        """正文容器内 script/style 内容不混入正文。"""
        c = _make_crawler()
        parsed = c.parse([{"url": "https://zhuanlan.zhihu.com/p/1", "html": _ARTICLE_HTML, "status": "ok"}])
        content = parsed[0]["content"]
        assert "不该出现" not in content
        assert ".noise" not in content

    def test_title_fallback_to_tag(self):
        """无 Post-Title 时回退 <title>（去掉 - 知乎 后缀）。"""
        c = _make_crawler()
        html = "<html><head><title>考研复试经验整理 - 知乎</title></head><body></body></html>"
        assert c._extract_title(html) == "考研复试经验整理"

    def test_login_wall_dropped(self):
        """正文含「登录后查看」→ 如实丢弃（合规，不爬登录内容）。"""
        c = _make_crawler()
        parsed = c.parse([{"url": "https://zhuanlan.zhihu.com/p/1", "html": _LOGIN_WALL_HTML, "status": "ok"}])
        assert parsed[0]["status"] == "failed"
        assert parsed[0]["content"] == ""
        assert "登录墙" in parsed[0]["error"]

    def test_fetch_error_item_kept_honestly(self):
        c = _make_crawler()
        parsed = c.parse(
            [{"url": "https://zhuanlan.zhihu.com/p/1", "html": "", "status": "error", "error": "超时"}]
        )
        assert parsed[0]["status"] == "failed"
        assert "超时" in parsed[0]["error"]


class TestStoreToReviewQueue:
    def test_store_creates_pending_queue_item(self, db_session):
        c = _make_crawler()
        items = c.parse(
            [{"url": "https://zhuanlan.zhihu.com/p/999", "html": _ARTICLE_HTML, "status": "ok"}]
        )
        inserted = c.store(items, db=db_session)
        assert inserted == 1

        ext = db_session.query(ExternalResearchItem).filter(
            ExternalResearchItem.source_url == "https://zhuanlan.zhihu.com/p/999"
        ).first()
        assert ext is not None
        assert ext.review_status == "PENDING"
        assert ext.item_type == "experience_post"
        assert ext.source_platform == "zhihu"
        assert ext.crawler_name == "zhihu_research"

        queue = db_session.query(ReviewQueueItem).filter(
            ReviewQueueItem.source_url == "https://zhuanlan.zhihu.com/p/999"
        ).first()
        assert queue is not None
        assert queue.review_status == "PENDING"

    def test_store_dedupes_same_url(self, db_session):
        c = _make_crawler()
        items = c.parse(
            [{"url": "https://zhuanlan.zhihu.com/p/888", "html": _ARTICLE_HTML, "status": "ok"}]
        )
        assert c.store(items, db=db_session) == 1
        assert c.store(items, db=db_session) == 0
