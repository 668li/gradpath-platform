"""就业方向爬虫 — 招聘平台岗位、薪资行情、面试经验、公司评价等数据源。

导入子模块以触发 @register_crawler 装饰器注册。
"""
from app.crawlers.career.boss_crawler import BossCrawler
from app.crawlers.career.lagou_crawler import LagouCrawler
from app.crawlers.career.interview_crawler import InterviewCrawler
from app.crawlers.career.review_crawler import ReviewCrawler
from app.crawlers.career.salary_crawler import SalaryCrawler

__all__ = [
    "BossCrawler",
    "LagouCrawler",
    "InterviewCrawler",
    "ReviewCrawler",
    "SalaryCrawler",
]
