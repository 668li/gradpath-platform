# backend/app/services/external_data_service.py
"""外部数据查询服务 — 公司元数据、薪资基准、市场宏观数据的列表与筛选。"""
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session

from app.core.cache import cache
from app.models.company import Company
from app.models.market_data import MarketData
from app.models.salary_benchmark import SalaryBenchmark
from app.services.employment_service import escape_like

# 默认查询上限
DEFAULT_LIMIT = 50
MAX_LIMIT = 200

# 公开数据缓存 TTL（秒）— 公司/薪资/市场数据更新频率极低（年更新），缓存 1 小时
PUBLIC_DATA_CACHE_TTL = 3600


def _model_to_dict(obj) -> dict | None:
    """将 SQLAlchemy 模型实例转为可 JSON 序列化的字典，用于缓存。

    - UUID/datetime 等非 JSON 原生类型由 cache.set 的 ``default=str`` 兜底转换
    - str 子类枚举（CompanySize/ExperienceLevel）本身就是字符串，保持原值
    """
    if obj is None:
        return None
    return {
        col.key: getattr(obj, col.key)
        for col in sa_inspect(obj).mapper.column_attrs
    }


def list_companies(
    db: Session,
    name: str | None = None,
    industry: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:
    """查询公司列表，支持 name 模糊搜索与 industry 精确筛选。

    结果按 (name, industry, limit) 缓存 1 小时（公开数据更新频率极低）。
    Redis 不可用时自动降级到直接查询 DB，不抛异常。
    """
    limit = min(max(limit, 1), MAX_LIMIT)
    cache_key = f"companies:list:{name}:{industry}:{limit}"

    try:
        cached = cache.get(cache_key)
    except Exception:
        cached = None
    if cached is not None:
        return cached

    query = db.query(Company)
    if name:
        query = query.filter(
            Company.name.ilike(f"%{escape_like(name)}%", escape="\\")
        )
    if industry:
        query = query.filter(Company.industry == industry)
    items = query.order_by(Company.name.asc()).limit(limit).all()

    result = [_model_to_dict(c) for c in items]
    try:
        cache.set(cache_key, result, ttl=PUBLIC_DATA_CACHE_TTL)
    except Exception:
        pass
    return result


def list_salary_benchmarks(
    db: Session,
    company: str | None = None,
    position: str | None = None,
    city: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:
    """查询薪资基准，支持 company/position/city 模糊筛选。

    结果按 (company, position, city, limit) 缓存 1 小时。
    """
    limit = min(max(limit, 1), MAX_LIMIT)
    cache_key = f"salary:list:{company}:{position}:{city}:{limit}"

    try:
        cached = cache.get(cache_key)
    except Exception:
        cached = None
    if cached is not None:
        return cached

    query = db.query(SalaryBenchmark)
    if company:
        query = query.filter(
            SalaryBenchmark.company.ilike(f"%{escape_like(company)}%", escape="\\")
        )
    if position:
        query = query.filter(
            SalaryBenchmark.position.ilike(f"%{escape_like(position)}%", escape="\\")
        )
    if city:
        query = query.filter(
            SalaryBenchmark.city.ilike(f"%{escape_like(city)}%", escape="\\")
        )
    items = (
        query.order_by(SalaryBenchmark.year.desc(), SalaryBenchmark.company.asc())
        .limit(limit)
        .all()
    )

    result = [_model_to_dict(s) for s in items]
    try:
        cache.set(cache_key, result, ttl=PUBLIC_DATA_CACHE_TTL)
    except Exception:
        pass
    return result


def list_market_data(
    db: Session,
    category: str | None = None,
    year: int | None = None,
    industry: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:
    """查询市场宏观数据，支持 category/year/industry 筛选。

    结果按 (category, year, industry, limit) 缓存 1 小时。
    """
    limit = min(max(limit, 1), MAX_LIMIT)
    cache_key = f"market:list:{category}:{year}:{industry}:{limit}"

    try:
        cached = cache.get(cache_key)
    except Exception:
        cached = None
    if cached is not None:
        return cached

    query = db.query(MarketData)
    if category:
        query = query.filter(MarketData.category == category)
    if year is not None:
        query = query.filter(MarketData.year == year)
    if industry:
        query = query.filter(MarketData.industry == industry)
    items = (
        query.order_by(MarketData.year.desc(), MarketData.indicator.asc())
        .limit(limit)
        .all()
    )

    result = [_model_to_dict(m) for m in items]
    try:
        cache.set(cache_key, result, ttl=PUBLIC_DATA_CACHE_TTL)
    except Exception:
        pass
    return result
