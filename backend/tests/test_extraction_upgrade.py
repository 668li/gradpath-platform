"""抽取升级黄金测试：trafilatura 正文抽取 + 通用列表页解析（夹具真实数据）。

夹具只读（sha256 封印）：
- hzau_detail.html：华中农业大学录取通知书公告详情页
- hzau_list.html：hzau 硕士招生列表页（boda 站点概况噪声 + PDF 附件混排）
- uestc_tz118.html：电子科大通知栏目列表页（现有正则 0 条，generic 应得 20 条）

trafilatura 不 mock，真库跑。
"""

import sys
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "official_announce"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crawlers.research.official_announce_crawler import (  # noqa: E402
    _extract_content_div,
    _parse_list_entries,
    extract_main_text,
    parse_list_generic,
)


def _read(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


# ===== 任务 1：trafilatura 正文抽取 =====


def test_extract_main_text_golden_hzau_detail():
    """黄金断言：trafilatura 抽出连续完整正文（正则路径做不到的两处）。"""
    text = extract_main_text(_read("hzau_detail.html"))
    # 中文连续无插空格（正则输出为"录取 通知书"形态，此连续句不可能出现）
    assert "录取通知书及相关材料于6月29日" in text
    # 尾部不截断，以落款日期结尾
    assert text.rstrip().endswith("2026年6月29日")


def test_regex_path_lacks_golden_sentence():
    """反向对照：旧正则输出不含该连续句 → 证明黄金断言验证的是新路径在起作用。"""
    old = _extract_content_div(_read("hzau_detail.html"), "v_news_content")
    assert old  # 旧路径本身非空（346 字形态），只是被打断/截尾
    assert "录取通知书及相关材料于6月29日" not in old


def test_extract_main_text_short_html_returns_empty():
    """短正文（<80 字）门槛：返回 "" 让调用方走原正则，与现状一致。"""
    assert extract_main_text("<html><body><p>很短</p></body></html>") == ""
    assert extract_main_text("") == ""


# ===== 任务 2：通用列表页解析 =====


def test_parse_list_generic_hzau_seven_htm_entries():
    """hzau 列表：.htm 恰好 7 条；含现有正则漏掉的 863968，排除误配的站点概况。"""
    entries = parse_list_generic(_read("hzau_list.html"), "https://yjs.hzau.edu.cn/zsgz/sszs.htm")
    htm = [e for e in entries if e["url"].endswith(".htm")]
    assert len(htm) == 7
    assert any("863968" in e["url"] for e in htm)  # 录取通知书公告（旧正则漏）
    assert not any("yjsjygk" in e["url"] for e in entries)  # 站点概况（旧正则误配）
    # 日期降序 + 归一化格式
    dates = [e["date"] for e in entries]
    assert dates == sorted(dates, reverse=True)
    assert all(len(d) == 10 and d[4] == "-" and d[7] == "-" for d in dates)


def test_parse_list_generic_uestc_twenty_entries():
    """uestc 列表（现有正则 0 条）：generic 得 20 条，首条 2026-01-12，全部同域绝对 URL。"""
    entries = parse_list_generic(_read("uestc_tz118.html"), "https://gr.uestc.edu.cn/tongzhi/118")
    assert len(entries) == 20
    assert entries[0]["date"] == "2026-01-12"
    assert all(e["url"].startswith("https://gr.uestc.edu.cn") for e in entries)


def test_parse_list_entries_dispatch_generic():
    """template=="generic" 分发到通用解析；既有两参调用（boda/news_list）行为不变。"""
    html = _read("uestc_tz118.html")
    base = "https://gr.uestc.edu.cn/tongzhi/118"
    assert _parse_list_entries(html, "generic", base) == parse_list_generic(html, base)
    boda_html = (
        '<ul><li><a href="/info/1010/123.htm">关于2026年复试分数线的公告</a>'
        "<span>2026-03-15</span></li></ul>"
    )
    assert _parse_list_entries(boda_html, "boda") == [
        {"url": "/info/1010/123.htm", "title": "关于2026年复试分数线的公告", "date": "2026-03-15"}
    ]
