"""地基②疫苗（spec 002 FR6）：eol_kaoyan 解析器录制样本测试。

2026-09-12 实录 kaoyan.eol.cn/nnews/ 列表页与一条详情页（真实页面存档于
tests/fixtures/eol_kaoyan/，与 official_announce 的 46 个样本同一模式）。

这是对抗死因①（目标站改版选择器漂移）的疫苗：改版当天本测试在合并前红掉，
而不是三周后发现库里是空的。红了只修解析纯函数/更新实录样本，地基不动。
"""

import re
from pathlib import Path
from urllib.parse import urljoin

from app.crawlers.research.eol_kaoyan_crawler import _LIST_ITEM_RE, _extract_detail_body

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "eol_kaoyan"
_LIST_BASE = "https://kaoyan.eol.cn/nnews/"


def _parse_list(html: str) -> list[dict]:
    """与 EolKaoyanCrawler.fetch 同构的纯解析（标题/URL/日期三元组）。"""
    entries = []
    for m in _LIST_ITEM_RE.finditer(html):
        title = re.sub(r"\s+", " ", m.group("title")).strip()
        url = urljoin(_LIST_BASE, m.group("url"))
        entries.append({"title": title, "url": url, "date": (m.group("date") or "").strip()})
    return entries


def test_list_fixture_parses_real_entries():
    html = (FIXTURES / "list_page.html").read_text(encoding="utf-8")
    entries = _parse_list(html)
    assert len(entries) >= 20, (
        f"实录列表页只解析出 {len(entries)} 条——若本断言红，kaoyan.eol.cn 结构已改版，"
        "请核对页面后更新解析纯函数与实录样本"
    )
    for e in entries[:5]:
        assert e["title"], "标题不得为空"
        assert e["url"].startswith("https://kaoyan.eol.cn/") and e["url"].endswith(".shtml")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", e["date"]), f"日期格式漂移: {e['date']!r}"
    # 实录内容锚点：2026-09-03 抓取当日的真实条目（防样本被偷换为垃圾页）
    titles = " ".join(e["title"] for e in entries)
    assert "推荐免试" in titles or "硕士" in titles, "实录内容锚点丢失——样本可能被偷换"


def test_detail_fixture_extracts_real_body():
    html = (FIXTURES / "detail_page.html").read_text(encoding="utf-8")
    body = _extract_detail_body(html)
    assert len(body) >= 200, "实录详情页应抽出足量正文（TRS_Editor 容器）"
    assert "硕士" in body, "实录正文锚点丢失——TRS 容器结构可能已改版"


def test_drifted_structure_yields_zero_not_garbage():
    """坏样本负例（验收判据 2）：结构漂移必须零产出，绝不静默吐垃圾。"""
    no_time_span = '<div class="fline"><a href="./202609/t1.shtml">标题</a></div>'  # 缺 time span
    assert list(_LIST_ITEM_RE.finditer(no_time_span)) == []
    no_trs_container = "<html><body><p>正文但无 TRS_Editor 容器</p></body></html>"
    assert _extract_detail_body(no_trs_container) == ""
    assert _extract_detail_body("") == ""
