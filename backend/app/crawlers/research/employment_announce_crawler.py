# backend/app/crawlers/research/employment_announce_crawler.py
"""高校就业网官方公告爬虫（就业专项 EMP-3，2026-09-30）。

与考研 official_announce 完全同一套管线（URL 级增量 / per-host 限速 / 单行记账 /
PENDING 审核队列），通过基类参数化点（item_type / 增量基线 / simhash / freshness
渠道）分流到就业语义——禁止子类绕过绑定点改 store（照 NewsAggregateCrawler 写
4 行子类而不参数化 = 就业条目污染考研去重基线的陷阱，任务书 §EMP-3 明令禁止）。

4 校栏目标定证据：docs/就业爬取类型调研-2026-09-30.md（parse_list_generic 实测
40/15/29/10 条，detail_url_re 过滤后 40/14/24/10，全 edu.cn 自建静态页）。
"""

from typing import Any

from app.crawlers.registry import register_crawler
from app.crawlers.research.official_announce_crawler import OfficialAnnounceCrawler

# 4 校栏目（EMP-2 标定，2026-09-30；扩校走调研报告 backlog 候选节）
EMPLOYMENT_SECTIONS: list[dict[str, Any]] = [
    {
        # 首页即聚合流（栏目列表页 URL 不可得：tzgg.htm/xxgg.htm 均空页）；
        # 博达 CMS：info/…htm 与 nry.jsp 两种详情形态
        "name": "山东大学就业信息网通知公告",
        "list_url": "https://job.sdu.edu.cn/",
        "detail_url_re": r"(info/\d+/\d+\.htm$|nry\.jsp\?urltype=news\.NewsContentUrl)",
        "cms": "generic",
    },
    {
        # ThinkPHP 系；URL 由首页 tab rel 属性实证（news/index/tag/tzgg）；
        # 正文容器 aContent（trafilatura 提取偏短时降级命中）
        "name": "中南大学就业信息网通知公告",
        "list_url": "https://career.csu.edu.cn/news/index/tag/tzgg",
        "detail_url_re": r"/news/view/aid/\d+/tag/tzgg$",
        "content_cls": "aContent",
        "cms": "generic",
    },
    {
        # 自建静态；备用二栏目 /recruitment /correcruit 见调研报告
        "name": "河北工业大学就业信息网重要通知",
        "list_url": "https://career.hebut.edu.cn/news/index.html",
        "detail_url_re": r"/news/content/id/\d+\.html$",
        "cms": "generic",
    },
    {
        # ASPX 动态但静态渲染；type 参数须 URL 编码
        "name": "华东理工大学就业信息网公告公示",
        "list_url": (
            "https://career.ecust.edu.cn/InformationNAVList.aspx"
            "?type=%E5%85%AC%E5%91%8A%E5%85%AC%E7%A4%BA&subinfotypedm=18"
        ),
        "detail_url_re": r"InformationDetail\.aspx\?XXID=\d+$",
        "cms": "generic",
    },
]


@register_crawler
class EmploymentAnnounceCrawler(OfficialAnnounceCrawler):
    """高校就业网官方公告（校招公告/宣讲会/双选会/选调通知）→ PENDING 审核队列。"""

    name = "employment_announce"
    category = "research"
    description = "高校就业网官方公告（4 校标定：山大/中南/河工大/华东理工，edu.cn）"
    DEFAULT_SECTIONS_OVERRIDE = EMPLOYMENT_SECTIONS
    # 参数化分流：入库/增量基线/simhash/freshness 全按就业语义（EMP-3 ①②③④）
    item_type = "employment_announce"
