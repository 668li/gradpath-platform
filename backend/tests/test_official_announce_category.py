"""official_announce category 打标防混标锁（2026-10-03）。

研招公告线打「研招公告·{栏目}」（grad_intel 院校公告接口按此前缀过滤）；
资讯聚合子类（eol/offcn）必须覆写为「考研资讯」前缀——它不是院校研招公告，
域名归口表虽会挡住它进院校公告接口，category 口径也必须区分。
"""

from app.crawlers.research.official_announce_crawler import (
    NewsAggregateCrawler,
    OfficialAnnounceCrawler,
)


def test_official_line_uses_yanzhao_prefix():
    c = OfficialAnnounceCrawler({})
    assert (
        c._kaoyan_category("复旦大学研究生院通知公告")
        == "研招公告·复旦大学研究生院通知公告"
    )


def test_news_aggregate_does_not_mislabel_as_yanzhao():
    c = NewsAggregateCrawler({})
    cat = c._kaoyan_category("中国教育在线·考研要闻")
    assert cat.startswith("考研资讯·"), "资讯聚合应打「考研资讯」前缀"
    assert not cat.startswith("研招公告"), "资讯聚合不得混入研招公告口径"


def test_employment_line_keeps_official_prefix():
    """就业线子类（item_type != kaoyan_news）不受影响：仍走官方公告·分支。"""
    assert OfficialAnnounceCrawler.kaoyan_category_prefix == "研招公告"
    # 就业线 tag 分支在 item_type 判定里，这里锁前缀属性本身不被就业线覆写
    from app.crawlers.research.employment_announce_crawler import (
        EmploymentAnnounceCrawler,
    )

    assert EmploymentAnnounceCrawler.item_type == "employment_announce"


def test_prefix_length_capped_at_50():
    c = OfficialAnnounceCrawler({})
    assert len(c._kaoyan_category("超" * 80)) <= 50
