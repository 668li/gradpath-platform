"""爬虫包入口 — 导入各分类包，触发 @register_crawler 装饰器完成全局注册。

B4 遗留修复：此前各分类 __init__ 已 import 各自子模块，但根 __init__ 为空，
run.py / admin API 只 import registry 空表，get_crawler() 恒返回 None，
导致 `python -m app.crawlers.run --source xxx` 与 admin /run 入口全部报
"爬虫未注册"。这里集中 import 各分类包，使任何入口拿到完整注册表。

2026-09-12 爬虫地基收敛（spec 002）：career/ real_data/ civil/ scrapy_grad/
四个目录已整体根除（退役假爬虫、一次性脚本堆、空壳、死亡实验），
只剩 grad / reports / research 三个分类包。
"""

from app.crawlers import grad  # noqa: F401
from app.crawlers import reports  # noqa: F401
from app.crawlers import research  # noqa: F401
