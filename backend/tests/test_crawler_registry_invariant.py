"""机器不变量：注册表 == 白名单（对抗审计 F6 修法·2026-09-06 第一批终态）。

历史病根：22+ 个注册爬虫挂着活代码，一次误加白名单/误触发即让预置合成数据
复活（581 假线、2187 假行均同源）。本批注销后，注册表里只应存在白名单成员。

由此产生一条永久闸：
- 新增爬虫必须先过合规评审进白名单，否则注册即红；
- 「注册但禁跑」的灰色地带被物理消灭，admin 列表不再有僵尸可选项。

成员名单写死 = 有意为之：扩白名单必须是一次显式的、带评审的 diff。
"""

import app.crawlers  # noqa: F401  # 触发包级全量注册（与运行时同一入口）
from app.crawlers import registry
from app.crawlers.compliance import ALLOWED_CRAWLER_SOURCES, is_allowed_crawler

# 2026-09-06 第一批终态的恰 10 名（zhihu/tieba 死源下架后）
EXPECTED_LIVE = {
    "real_data",
    "yanzhao",
    "yanzhao_program",
    "bilibili_research",
    "web_article_research",
    "rss_news_research",
    "eol_kaoyan",
    "official_announce",
    "rsshub_research",
    "news_aggregates",
}


def test_registry_equals_whitelist():
    """实载注册表与合规白名单必须一字不差相等。"""
    assert set(registry._REGISTRY) == set(ALLOWED_CRAWLER_SOURCES)


def test_whitelist_membership_frozen():
    """白名单成员冻结为 10 名；改动必须同步本测试＝强制显式评审。"""
    assert set(ALLOWED_CRAWLER_SOURCES) == EXPECTED_LIVE
    assert len(ALLOWED_CRAWLER_SOURCES) == 10


def test_retired_sources_gone_from_registry():
    """已退役名不得再出现在注册表（防复活）。"""
    retired = {
        "adjustment",
        "adjustment_real",
        "bilibili_kaoyan",
        "dark_knowledge",
        "forum_experience",
        "github_datasets",
        "github_kaoyan",
        "grad_forum",
        "mentor",
        "mentor_review_aggregator",
        "pdf_report",
        "retest_experience",
        "stats_importer",
        "zhihu_research",
        "tieba_research",
        "salary_expand",
    }
    revived = retired & set(registry._REGISTRY)
    assert revived == set(), f"退役爬虫复活注册: {revived}"
    for name in retired:
        assert not is_allowed_crawler(name)
