"""外部调研能力爬虫 — 在产：eol_kaoyan / official_announce(+news_aggregates) /
rsshub_research / rss_news / web_article / bilibili_research，及纯函数支撑模块
（dedup / quality / transformer / news_meta / experience_quality）。

2026-09-12 爬虫地基收敛（spec 002）：zhihu / tieba / v2ex_knowledge /
bilibili_kaoyan / github_kaoyan 五个退役或孤儿文件已物理删除
（zhihu/tieba 属 WAF 红线退役；后三者为无注册孤儿）。git 历史可考古。
"""

from app.crawlers.research import bilibili_research_crawler  # noqa: F401
from app.crawlers.research import eol_kaoyan_crawler  # noqa: F401
from app.crawlers.research import official_announce_crawler  # noqa: F401
from app.crawlers.research import rss_news_crawler  # noqa: F401
from app.crawlers.research import rsshub_research_crawler  # noqa: F401
from app.crawlers.research import web_article_crawler  # noqa: F401
