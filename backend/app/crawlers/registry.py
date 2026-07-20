"""爬虫注册表 — 管理所有已注册的爬虫。"""
from typing import Type
from app.crawlers.base_crawler import BaseCrawler

_REGISTRY: dict[str, Type[BaseCrawler]] = {}

def register_crawler(cls: Type[BaseCrawler]) -> Type[BaseCrawler]:
    """装饰器：注册爬虫类。"""
    if not cls.name:
        raise ValueError(f"爬虫 {cls.__name__} 缺少 name 属性")
    _REGISTRY[cls.name] = cls
    return cls

def get_crawler(name: str) -> Type[BaseCrawler] | None:
    """按名称获取爬虫类。"""
    return _REGISTRY.get(name)

def list_crawlers() -> dict[str, Type[BaseCrawler]]:
    """列出所有已注册爬虫。"""
    return dict(_REGISTRY)

def list_crawlers_by_category(category: str) -> dict[str, Type[BaseCrawler]]:
    """按分类列出爬虫。"""
    return {k: v for k, v in _REGISTRY.items() if v.category == category}
