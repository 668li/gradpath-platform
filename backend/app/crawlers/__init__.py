"""爬虫包入口 — 导入各分类包，触发 @register_crawler 装饰器完成全局注册。

B4 遗留修复：此前各分类 __init__ 已 import 各自子模块，但根 __init__ 为空，
run.py / admin API 只 import registry 空表，get_crawler() 恒返回 None，
导致 `python -m app.crawlers.run --source xxx` 与 admin /run 入口全部报
"爬虫未注册"。这里集中 import 各分类包，使任何入口拿到完整注册表。
"""

from app.crawlers import career  # noqa: F401
from app.crawlers import grad  # noqa: F401
from app.crawlers import real_data  # noqa: F401
from app.crawlers import reports  # noqa: F401
from app.crawlers import research  # noqa: F401
