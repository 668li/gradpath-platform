# -*- coding: utf-8 -*-
"""stats_gongbao_scraper 单元测试：用 2025 公报真实片段断言正则抽取与白名单校验。"""
import pytest

from app.crawlers.real_data.stats_gongbao_scraper import (
    extract_gongbao_metrics,
    strip_to_text,
    validate_gongbao_url,
)

URL_2025 = "https://www.stats.gov.cn/sj/zxfb/202602/t20260228_1962662.html"

# 摘自《2025年国民经济和社会发展统计公报》真实正文（保留注释标记 [7]/[8]/[63]）
GONGBAO_2025_FRAGMENT = (
    "年末全国就业人员 72504 万人，其中城镇就业人员 47535 万人，"
    "占全国就业人员比重为 65.6%。全年全国城镇新增就业[7]1267 万人，"
    "比上年多增 25 万人。全年全国城镇调查失业率平均值为 5.2%，"
    "比上年下降 0.1 个百分点。年末全国城镇调查失业率为 5.1%。"
    "全国农民工[8]总量 30115 万人，比上年下降 0.5%。其中，外出农民工 17901 万人，"
    "本地农民工 12214 万人。全年全国居民人均可支配收入 43377 元，"
    "比上年名义增长 3.2%，扣除价格因素实际增长 2.9%。按常住地分，"
    "城镇居民人均可支配收入 56502 元，比上年名义增长 3.1%；"
    "农村居民人均可支配收入 24456 元，比上年名义增长 5.8%。"
    "全国居民人均可支配收入中位数[63]36231 元，比上年名义增长 1.6%。"
)


def test_extract_all_2025_metrics():
    recs = extract_gongbao_metrics(GONGBAO_2025_FRAGMENT, 2025, URL_2025, "2026-02-28")
    assert len(recs) == 8
    by = {(r["indicator"], r["category"]): r for r in recs}

    assert by[("全国就业人员数", "全体")]["value"] == 72504
    assert by[("城镇就业人员数", "全体")]["value"] == 47535
    assert by[("城镇新增就业人数", "全体")]["value"] == 1267
    assert by[("城镇调查失业率", "全体")]["value"] == 5.2
    assert by[("农民工总量", "全体")]["value"] == 30115
    assert by[("全国居民人均可支配收入", "全体")]["value"] == 43377
    assert by[("全国居民人均可支配收入", "城镇")]["value"] == 56502
    assert by[("全国居民人均可支配收入", "农村")]["value"] == 24456


def test_record_shape_and_source():
    recs = extract_gongbao_metrics(GONGBAO_2025_FRAGMENT, 2025, URL_2025, "2026-02-28")
    for r in recs:
        assert r["source"] == "国家统计局"
        assert r["source_url"] == URL_2025
        assert r["published_at"] == "2026-02-28"
        assert r["year"] == 2025
        assert r["region"] is None and r["industry"] is None
        assert isinstance(r["value"], float)
        assert r["unit"] in ("万人", "%", "元/年")


def test_median_not_misparsed_as_income():
    """中位数句不得污染：36231 是"中位数"，不是人均可支配收入真值。"""
    recs = extract_gongbao_metrics(GONGBAO_2025_FRAGMENT, 2025, URL_2025, "2026-02-28")
    values = [r["value"] for r in recs if r["indicator"] == "全国居民人均可支配收入"]
    assert 36231 not in values
    assert 43377 in values


def test_missing_pattern_yields_empty():
    assert extract_gongbao_metrics("没有指标的文本", 2025, URL_2025, "x") == []


def test_strip_to_text_removes_tags():
    html = "<html><script>var x=1;</script><p>年末全国就业人员<b>72504</b>万人</p></html>"
    text = strip_to_text(html)
    assert "script" not in text
    assert "年末全国就业人员 72504 万人" in text


@pytest.mark.parametrize("bad_url", [
    "http://www.stats.gov.cn/sj/zxfb/202602/t20260228_1962662.html",  # 非 https
    "https://evil.example.com/sj/zxfb/202602/t20260228_1962662.html",  # 非白名单 host
    "https://www.stats.gov.cn/other/t20260228_1962662.html",           # 非公报路径
    "https://www.stats.gov.cn/sj/zxfb/../../etc/passwd",               # 路径穿越尝试
    "file:///etc/passwd",
])
def test_validate_rejects_non_whitelist(bad_url):
    with pytest.raises(ValueError):
        validate_gongbao_url(bad_url)


def test_validate_accepts_whitelisted():
    assert validate_gongbao_url(URL_2025) == URL_2025
