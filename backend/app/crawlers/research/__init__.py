"""外部调研能力爬虫 — 网页文章、RSS 资讯、B站视频等公开信息源调研与汇总。

导入子模块以触发 @register_crawler 装饰器注册。

B4 补注册：bilibili_kaoyan / github_kaoyan / v2ex_knowledge 三个调研爬虫此前
未随包导入，导致注册表里找不到但 crawler 文件一直存在（半启用状态）。
"""
from app.crawlers.research import bilibili_kaoyan  # noqa: F401
from app.crawlers.research import bilibili_research_crawler  # noqa: F401
from app.crawlers.research import eol_kaoyan_crawler  # noqa: F401
from app.crawlers.research import github_kaoyan  # noqa: F401
from app.crawlers.research import official_announce_crawler  # noqa: F401
from app.crawlers.research import rss_news_crawler  # noqa: F401
from app.crawlers.research import rsshub_research_crawler  # noqa: F401
from app.crawlers.research import tieba_research_crawler  # noqa: F401
from app.crawlers.research import v2ex_knowledge  # noqa: F401
from app.crawlers.research import web_article_crawler  # noqa: F401
from app.crawlers.research import zhihu_research_crawler  # noqa: F401
