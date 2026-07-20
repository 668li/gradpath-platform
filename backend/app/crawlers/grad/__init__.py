"""考研方向爬虫 — 研招网、各院校招生简章、论坛报录比、分数线、导师信息等数据源。

导入子模块以触发 @register_crawler 装饰器注册。
"""
from app.crawlers.grad import yanzhao_crawler  # noqa: F401
from app.crawlers.grad import forum_crawler  # noqa: F401
from app.crawlers.grad import scoreline_crawler  # noqa: F401
from app.crawlers.grad import scoreline_real_crawler  # noqa: F401
from app.crawlers.grad import adjustment_crawler  # noqa: F401
from app.crawlers.grad import mentor_crawler  # noqa: F401
from app.crawlers.grad import mentor_review_aggregator  # noqa: F401
from app.crawlers.grad import admission_ratio_crawler  # noqa: F401
from app.crawlers.grad import dark_knowledge_crawler  # noqa: F401
from app.crawlers.grad import forum_experience_crawler  # noqa: F401
from app.crawlers.grad import retest_experience_crawler  # noqa: F401
from app.crawlers.grad import adjustment_real_crawler  # noqa: F401
from app.crawlers.grad import real_data_crawler  # noqa: F401
from app.crawlers.grad import mentor_scraper  # noqa: F401
