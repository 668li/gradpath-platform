"""外部调研能力爬虫 — 网页文章、RSS 资讯、B站视频等公开信息源调研与汇总。

导入子模块以触发 @register_crawler 装饰器注册。
"""
from app.crawlers.research import bilibili_research_crawler  # noqa: F401
from app.crawlers.research import rss_news_crawler  # noqa: F401
from app.crawlers.research import web_article_crawler  # noqa: F401
