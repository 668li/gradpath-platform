"""official_announce 列表模板解析测试。

覆盖：boda 模板（<li><a>标题</a><span>日期</span></li>）与
news_list 模板（苏州大学等 news-list-item CMS，日期为 <span>日</span><b>YYYY.MM</b>）。
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crawlers.research.official_announce_crawler import (
    _auto_detect_content_cls,
    _parse_list_entries,
)

BODA_HTML = (
    '<ul><li><a href="/info/1010/123.htm">关于2026年复试分数线的公告</a>'
    "<span>2026-03-15</span></li></ul>"
)

NEWS_LIST_HTML = (
    '<li class="news-list-item">'
    '<a href="/da/52/c8386a711250/page.htm" title="关于接收2027级推荐免试研究生（含直博生）预报名的通知">'
    "<div class=\"date\"><span>10</span><b>2026.08</b></div>"
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
        "<div class=\"content\"><h3>关于2026年拟录取研究生党团组织关系转接的说明</h3></div></a></li>"
        '<li class="news-list-item"><a href="/97/06/c8386a694022/page.htm" '
        'title="苏州大学2026年硕士研究生第四轮接收调剂公告">'
        '<div class="date"><span>28</span><b>2026.4</b></div>'
        "<div class=\"content\"><h3>第四轮调剂</h3></div></a></li>"
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
