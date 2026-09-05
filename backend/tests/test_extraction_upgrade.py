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


# ===== 任务 3（2026-09-05 扩校）：九校官方栏目真实夹具黄金测试 =====
#
# 夹具全部来自 2026-09-05 当天真实抓取（scripts/calibrate_official_announce.py，
# robots+SSRF+2s 限速护栏），非缓存旧页。sha256 封印（真实抓取存证）：
# - xjtu_list.html  950efebf17cf6a821a2fd32fe8a7d53b5496cfbdf85d744b93003cc3529d6e15
#   西安交通大学研究生院招生工作栏（gs.xjtu.edu.cn/tzgg/zsgz.htm，14 条全部 /info/）
# - whu_list.html   f7064e051d65ba4045ccdbc299c0097436551a3f2df2d41966a97518cfd03b6d
#   武汉大学研究生院首页（gs.whu.edu.cn，63 条，43 条 /info/）
# - hust_list.html  aa964ad9fa96ca63215af56c6ab1570c8c4f2635e3ef38d0458eba6853fed255
#   华中科技大学研究生院首页（gs.hust.edu.cn，34 条全部 /info/）
# - seu_list.html   cac79fc9df24613f2108876dc1080015110654210b0c6d6c1fee2f38ce3d9ac4
#   东南大学研究生院首页（seugs.seu.edu.cn，85 条，81 条 /page.htm）
# - scu_list.html   05abe932e282cf25bf5e974aeb53681c88eeaac56a1e7649b392023bfa7df6ff
#   四川大学研招网首页（yz.scu.edu.cn，13 条，7 条 /zsxx/Details/<uuid>）
# - sdu_list.html   ad4758511c7e6f12bb51b73b70789d4b734da2ba99289633e3e88a2261b3fb8c
#   山东大学研招网首页（yz.sdu.edu.cn，14 条全部 /info/）
# - tju_list.html   1f95f45fc837e83f067d0ccbc1c10074e36cbd8dbab7902562c22f8d06d87af4
#   天津大学研究生院首页（gs.tju.edu.cn，13 条，11 条 /info/）
# - xmu_list.html   c0fe7c39e4bdc6f099684ca70c049aa44071b98ae14930dc0ae252f0e3e9cdad
#   厦门大学研究生院首页（gs.xmu.edu.cn，32 条，31 条 /info/）
# - cqu_list.html   144571a8222a241faa3fcfcfa5e4acf49d1ff1553e3c828fc38d6e9ff39a17cc
#   重庆大学研招网首页（yz.cqu.edu.cn，6 条全部 /news/YYYY-MM/N.html）
# - tju_detail.html 8eebe126308e2cbce0c9896285d891ab127346fba743898a1880d27189ef2098
#   天大研究生院详情页（gs.tju.edu.cn/info/1181/14212.htm，trafilatura 正文 1082 字）

import hashlib  # noqa: E402
import re  # noqa: E402
from urllib.parse import urlparse  # noqa: E402

import pytest  # noqa: E402

# key: (列表页 base_url, detail_url_re, detail_url_re 过滤后条数, 标定时实测最新日期)
_EXPANSION_SCHOOLS = {
    "whu": ("https://gs.whu.edu.cn/", r"/info/\d+/\d+\.htm", 43, "2026-09-03"),
    "hust": ("https://gs.hust.edu.cn/", r"/info/\d+/\d+\.htm", 34, "2026-09-03"),
    "xjtu": ("https://gs.xjtu.edu.cn/tzgg/zsgz.htm", r"/info/\d+/\d+\.htm", 14, "2026-06-26"),
    "seu": ("https://seugs.seu.edu.cn/", r"/page\.htm$", 81, "2026-09-04"),
    "scu": ("https://yz.scu.edu.cn/", r"/zsxx/Details/[0-9a-f-]{36}", 7, "2026-09-05"),
    "sdu": ("https://yz.sdu.edu.cn/", r"/info/\d+/\d+\.htm", 14, "2026-06-29"),
    "tju": ("https://gs.tju.edu.cn/", r"/info/\d+/\d+\.htm", 11, "2026-09-04"),
    "xmu": ("https://gs.xmu.edu.cn/", r"/info/\d+/\d+\.htm", 31, "2026-09-04"),
    "cqu": ("https://yz.cqu.edu.cn/", r"/news/\d{4}-\d{2}/\d+\.html", 6, "2026-05-29"),
}

# 18 个月新鲜线（2026-09-05 标定）
_EXPANSION_FRESH_CUTOFF = "2025-03-05"


@pytest.mark.parametrize("key", sorted(_EXPANSION_SCHOOLS))
def test_expansion_school_list(key):
    """九校扩校黄金断言：条数≥5（detail_url_re 过滤后）、日期降序且新鲜、URL 同域。

    每校锁定四个标定值：过滤后条数、实测最新日期（防夹具/解析退化）、
    新鲜线（≤18 个月）、同域护栏（parse_list_generic 不出域）。
    """
    base, detail_re, matched_n, newest = _EXPANSION_SCHOOLS[key]
    entries = parse_list_generic(_read(f"{key}_list.html"), base)

    # 空列表直接不合格（≥5 条硬线）
    assert entries, f"{key}: 列表页解析为空"
    matched = [e for e in entries if re.search(detail_re, e["url"])]
    assert len(matched) >= 5, f"{key}: detail_url_re 过滤后仅 {len(matched)} 条"
    assert len(matched) == matched_n, f"{key}: 过滤后条数偏离标定值 {matched_n}"

    # 日期：降序 + 最新日期锚定标定值 + 18 个月新鲜线
    dates = [e["date"] for e in entries]
    assert dates == sorted(dates, reverse=True)
    assert entries[0]["date"] == newest, f"{key}: 最新日期 {entries[0]['date']} != 标定 {newest}"
    assert newest >= _EXPANSION_FRESH_CUTOFF, f"{key}: 最新日期超出 18 个月"

    # URL 同域（忽略 www.），且为绝对 http(s) URL
    host = (urlparse(base).hostname or "").lower().removeprefix("www.")
    for e in entries:
        parsed = urlparse(e["url"])
        assert parsed.scheme in ("http", "https"), f"{key}: 非绝对 URL {e['url']}"
        assert (parsed.hostname or "").lower().removeprefix("www.") == host, (
            f"{key}: 跨域条目 {e['url']}"
        )


def test_expansion_tju_detail_extract_main_text():
    """tju 详情页夹具（新扩校 CMS 代表）：trafilatura 抽出 ≥80 字正文。"""
    text = extract_main_text(_read("tju_detail.html"))
    assert len(text) >= 80
