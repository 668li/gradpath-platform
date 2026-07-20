"""考公方向爬虫 — 国考/省考职位表、报录比、待遇信息等数据源。

导入子模块以触发 @register_crawler 装饰器注册。
"""
from app.crawlers.civil.guokao_crawler import GuokaoCrawler  # noqa: F401
from app.crawlers.civil.shengkao_crawler import ShengkaoCrawler  # noqa: F401
from app.crawlers.civil.ratio_crawler import RatioCrawler  # noqa: F401
from app.crawlers.civil.salary_crawler import SalaryCrawler  # noqa: F401

__all__ = ["GuokaoCrawler", "ShengkaoCrawler", "RatioCrawler", "SalaryCrawler"]
