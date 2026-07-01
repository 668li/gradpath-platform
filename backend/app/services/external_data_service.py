# backend/app/services/external_data_service.py
"""外部数据查询服务 — 公司元数据、薪资基准、市场宏观数据的列表与筛选。"""
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.market_data import MarketData
from app.models.salary_benchmark import SalaryBenchmark
from app.services.employment_service import escape_like

# 默认查询上限
DEFAULT_LIMIT = 50
MAX_LIMIT = 200


def list_companies(
    db: Session,
    name: str | None = None,
    industry: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[Company]:
    """查询公司列表，支持 name 模糊搜索与 industry 精确筛选。"""
    query = db.query(Company)
    if name:
        query = query.filter(
            Company.name.ilike(f"%{escape_like(name)}%", escape="\\")
        )
    if industry:
        query = query.filter(Company.industry == industry)
    limit = min(max(limit, 1), MAX_LIMIT)
    return query.order_by(Company.name.asc()).limit(limit).all()


def list_salary_benchmarks(
    db: Session,
    company: str | None = None,
    position: str | None = None,
    city: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[SalaryBenchmark]:
    """查询薪资基准，支持 company/position/city 模糊筛选。"""
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
    limit = min(max(limit, 1), MAX_LIMIT)
    return (
        query.order_by(SalaryBenchmark.year.desc(), SalaryBenchmark.company.asc())
        .limit(limit)
        .all()
    )


def list_market_data(
    db: Session,
    category: str | None = None,
    year: int | None = None,
    industry: str | None = None,
    limit: int = DEFAULT_LIMIT,
) -> list[MarketData]:
    """查询市场宏观数据，支持 category/year/industry 筛选。"""
    query = db.query(MarketData)
    if category:
        query = query.filter(MarketData.category == category)
    if year is not None:
        query = query.filter(MarketData.year == year)
    if industry:
        query = query.filter(MarketData.industry == industry)
    limit = min(max(limit, 1), MAX_LIMIT)
    return (
        query.order_by(MarketData.year.desc(), MarketData.indicator.asc())
        .limit(limit)
        .all()
    )
