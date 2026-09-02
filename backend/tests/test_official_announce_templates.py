"""official_announce 列表模板解析测试。

覆盖：boda 模板（<li><a>标题</a><span>日期</span></li>）与
news_list 模板（苏州大学等 news-list-item CMS，日期为 <span>日</span><b>YYYY.MM</b>）。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crawlers.research.official_announce_crawler import (
    _auto_detect_content_cls,
    _parse_list_entries,
    parse_detail_markdown,
    OfficialAnnounceCrawler,
)

BODA_HTML = (
    '<ul><li><a href="/info/1010/123.htm">关于2026年复试分数线的公告</a>'
    "<span>2026-03-15</span></li></ul>"
)

NEWS_LIST_HTML = (
    '<li class="news-list-item">'
    '<a href="/da/52/c8386a711250/page.htm" title="关于接收2027级推荐免试研究生（含直博生）预报名的通知">'
    '<div class="date"><span>10</span><b>2026.08</b></div>'
    '<div class="content"><h3 class="text-truncate">正文标题</h3></div>'
    "</a></li>"
)


def test_boda_template_parse():
    entries = _parse_list_entries(BODA_HTML, "boda")
    assert entries == [
        {"url": "/info/1010/123.htm", "title": "关于2026年复试分数线的公告", "date": "2026-03-15"}
    ]


def test_news_list_template_parse():
    entries = _parse_list_entries(NEWS_LIST_HTML, "news_list")
    assert len(entries) == 1
    e = entries[0]
    assert e["url"] == "/da/52/c8386a711250/page.htm"
    assert "推荐免试" in e["title"]
    assert e["date"] == "2026-08-10"  # 月/日补零归一化


def test_news_list_template_realistic_suda_page():
    # 与苏州大学 8386/list.htm 实测结构一致的完整片段
    html = (
        '<div class="news-list"><ul>'
        '<li class="news-list-item"><a href="/a1/0a/c8386a696586/page.htm" '
        'title="关于2026年拟录取研究生党团组织关系转接的说明">'
        '<div class="date"><span>5</span><b>2026.6</b></div>'
        '<div class="content"><h3>关于2026年拟录取研究生党团组织关系转接的说明</h3></div></a></li>'
        '<li class="news-list-item"><a href="/97/06/c8386a694022/page.htm" '
        'title="苏州大学2026年硕士研究生第四轮接收调剂公告">'
        '<div class="date"><span>28</span><b>2026.4</b></div>'
        '<div class="content"><h3>第四轮调剂</h3></div></a></li>'
        "</ul></div>"
    )
    entries = _parse_list_entries(html, "news_list")
    assert [e["date"] for e in entries] == ["2026-06-05", "2026-04-28"]
    assert all(e["url"].endswith("page.htm") for e in entries)


def test_auto_detect_content_cls_prefers_filled_container():
    html = (
        '<div class="v_news_content"><p>太短</p></div>'
        '<div class="TRS_Editor"><p>' + "正文内容。" * 40 + "</p></div>"
    )
    assert _auto_detect_content_cls(html) == "TRS_Editor"


def test_auto_detect_content_cls_empty():
    assert _auto_detect_content_cls("<div class='x'></div>") == ""


# ===== parse_detail_markdown 测试 =====


def test_parse_markdown_strips_formatting():
    result = parse_detail_markdown("# 标题 **加粗** [链接](http://x.com) *斜*")
    assert "标题" in result
    assert "加粗" in result
    assert "链接" in result
    assert "斜" in result
    assert "**" not in result
    assert "[" not in result


def test_parse_markdown_empty():
    assert parse_detail_markdown("") == ""
    assert parse_detail_markdown(None) == ""  # type: ignore[arg-type]


def test_parse_markdown_removes_image_links():
    text = "正文内容 ![图片](http://img.com/a.png) 继续"
    result = parse_detail_markdown(text)
    assert "继续" in result
    assert "![图片]" not in result


def test_parse_markdown_removes_code_blocks():
    text = "```python\nprint('hello')\n```\n后续"
    result = parse_detail_markdown(text)
    assert "后续" in result
    assert "```" not in result


# ===== use_browser 模式测试 =====


class TestOfficialAnnounceUseBrowser:
    def test_use_browser_false_by_default(self):
        """use_browser 默认关闭，不影响现有行为。"""
        c = OfficialAnnounceCrawler()
        assert not c._use_browser

    def test_use_browser_true_configured(self):
        """config 设置 use_browser=True 后生效。"""
        c = OfficialAnnounceCrawler({"use_browser": True})
        assert c._use_browser

    def test_use_browser_true_renders_via_crawl4ai(self, monkeypatch):
        """use_browser=True 时 _fetch_detail 优先走 fetch_markdown。"""
        c = OfficialAnnounceCrawler({"use_browser": True})

        # 模拟 fetch_markdown 返回成功结果
        mock_result = type(
            "R",
            (),
            {
                "success": True,
                "markdown": "## 标题\n正文段落",
                "title": "页面标题",
                "error_message": "",
            },
        )()
        monkeypatch.setattr(c, "fetch_markdown", lambda url, **k: mock_result)

        title, body = c._fetch_detail(
            "https://yjs.hzau.edu.cn/xxx.htm", "v_news_content", "-华中农业大学研究生院"
        )
        assert title == "页面标题"
        assert "正文段落" in body
        assert "##" not in body  # markdown 语法被 parse_detail_markdown 剥离

    def test_use_browser_fallback_on_failure(self, monkeypatch):
        """crawl4ai 渲染失败 → 降级 HTTP 正则抽取。"""
        c = OfficialAnnounceCrawler({"use_browser": True})

        # 模拟 fetch_markdown 返回失败结果
        mock_result = type(
            "R",
            (),
            {
                "success": False,
                "markdown": "",
                "title": "",
                "error_message": "render failed",
            },
        )()
        monkeypatch.setattr(c, "fetch_markdown", lambda url, **k: mock_result)

        # 模拟 HTTP 路径正常
        html = "<html><title>公告标题-华中农业大学研究生院</title><body><div class='v_news_content'>正文内容</div></body></html>"
        monkeypatch.setattr(
            c, "_request", lambda url, **k: type("Resp", (), {"encoding": "utf-8", "text": html})()
        )

        title, body = c._fetch_detail(
            "https://yjs.hzau.edu.cn/xxx.htm", "v_news_content", "-华中农业大学研究生院"
        )
        assert title == "公告标题"
        assert "正文内容" in body

    def test_use_browser_markdown_empty_fallback(self, monkeypatch):
        """crawl4ai markdown 为空 → 降级 HTTP。"""
        c = OfficialAnnounceCrawler({"use_browser": True})

        mock_result = type(
            "R",
            (),
            {
                "success": True,
                "markdown": "",
                "title": "",
                "error_message": "",
            },
        )()
        monkeypatch.setattr(c, "fetch_markdown", lambda url, **k: mock_result)

        html = "<html><title>标题</title><body><div class='v_news_content'>正文</div></body></html>"
        monkeypatch.setattr(
            c, "_request", lambda url, **k: type("Resp", (), {"encoding": "utf-8", "text": html})()
        )

        title, body = c._fetch_detail("https://yjs.hzau.edu.cn/xxx.htm", "v_news_content", "")
        assert title == "标题"
        assert "正文" in body

    def test_use_browser_client_unavailable_fallback(self, monkeypatch):
        """crawl4ai 客户端不可用（fetch_markdown 返回 None）→ 降级 HTTP。"""
        c = OfficialAnnounceCrawler({"use_browser": True})
        monkeypatch.setattr(c, "fetch_markdown", lambda url, **k: None)

        html = "<html><title>标题</title><body><div class='v_news_content'>正文</div></body></html>"
        monkeypatch.setattr(
            c, "_request", lambda url, **k: type("Resp", (), {"encoding": "utf-8", "text": html})()
        )

        title, body = c._fetch_detail("https://yjs.hzau.edu.cn/xxx.htm", "v_news_content", "")
        assert title == "标题"
        assert "正文" in body

    def test_use_browser_false_uses_http(self, monkeypatch):
        """use_browser=False 时 _fetch_detail 走原 HTTP 路径，不碰 crawl4ai。"""
        c = OfficialAnnounceCrawler({"use_browser": False})

        called = {"fetch_markdown": False}
        monkeypatch.setattr(
            c, "fetch_markdown", lambda url, **k: called.update(fetch_markdown=True)
        )
        html = "<html><title>标题</title><body><div class='v_news_content'>正文</div></body></html>"
        monkeypatch.setattr(
            c, "_request", lambda url, **k: type("Resp", (), {"encoding": "utf-8", "text": html})()
        )

        c._fetch_detail("https://yjs.hzau.edu.cn/xxx.htm", "v_news_content", "")
        assert not called["fetch_markdown"]
