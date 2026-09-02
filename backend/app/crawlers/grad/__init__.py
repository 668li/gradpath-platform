"""考研方向爬虫 — 研招网、各院校招生简章、论坛报录比、分数线、导师信息等数据源。

导入子模块以触发 @register_crawler 装饰器注册。
"""

# 注：scoreline_crawler / scoreline_real_crawler / admission_ratio_crawler
# 三个爬虫是程序合成假数据生成器（伪造"院校研究生院官网/研招网"来源标签，
# 直插业务表绕过审核队列），已隔离注销（2026-09-02，grad_scoreline_records
# 581+90 条假数据已删）。不移除文件，保留历史与审计需要。若需重新注册，
# 须先走真实数据 + PENDING 审核队列改造，否则会再次污染业务表。

from app.crawlers.grad import adjustment_crawler  # noqa: F401
from app.crawlers.grad import adjustment_real_crawler  # noqa: F401
from app.crawlers.grad import dark_knowledge_crawler  # noqa: F401
from app.crawlers.grad import forum_crawler  # noqa: F401
from app.crawlers.grad import forum_experience_crawler  # noqa: F401
from app.crawlers.grad import mentor_crawler  # noqa: F401
from app.crawlers.grad import mentor_review_aggregator  # noqa: F401
from app.crawlers.grad import mentor_scraper  # noqa: F401
from app.crawlers.grad import real_data_crawler  # noqa: F401
from app.crawlers.grad import retest_experience_crawler  # noqa: F401
from app.crawlers.grad import yanzhao_crawler  # noqa: F401
