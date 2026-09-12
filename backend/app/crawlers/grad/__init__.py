"""考研方向爬虫 — 在产：real_data_crawler（高校官网抓取）、yanzhao（招生简章）。

导入子模块以触发 @register_crawler 装饰器注册。

历史注记（2026-09-12）：scoreline_crawler / scoreline_real_crawler /
admission_ratio_crawler 三个程序合成假数据生成器（伪造"院校研究生院官网/研招网"
来源标签，直插业务表绕过审核队列，581+90 条假数据判例），以及 dark_knowledge /
mentor×2 / forum×3 / adjustment×2 / mentor_scraper 等 @RETIRED 退役文件，
已随爬虫地基收敛（spec 002）**物理删除**——git 历史可考古，工作区不可复活。
重新注册任何退役名前，必须先过真实数据 + PENDING 审核队列改造 + 合规评审。
"""

from app.crawlers.grad import real_data_crawler  # noqa: F401
from app.crawlers.grad import yanzhao_crawler  # noqa: F401
