# backend/tests/test_external_data_cache.py
"""外部数据服务缓存测试 — 验证 RedisCache 集成。

覆盖：
- 缓存命中：第二次调用相同参数应直接返回缓存值，不打 DB
- 缓存未命中：首次调用打 DB 并写缓存
- 不同参数不命中缓存
- Redis 不可用时降级到直接打 DB（不抛异常）
"""
from unittest.mock import patch

import pytest
from sqlalchemy import event

from app.core.cache import cache
from app.seed.seed_companies import seed_companies
from app.seed.seed_market_data import seed_market_data
from app.seed.seed_salary_benchmarks import seed_salary_benchmarks
from app.services.external_data_service import (
    list_companies,
    list_market_data,
    list_salary_benchmarks,
)


# ======================================================================
# 辅助函数与 fixture
# ======================================================================

def _count_queries(db_session, func):
    """统计 func 执行期间发生的 SQL 查询次数。"""
    query_count = 0

    @event.listens_for(db_session.bind, "before_cursor_execute")
    def _counter(*args, **kwargs):
        nonlocal query_count
        query_count += 1

    try:
        result = func()
    finally:
        event.remove(db_session.bind, "before_cursor_execute", _counter)
    return result, query_count


@pytest.fixture
def seeded_db(db_session):
    """加载全部种子数据到测试数据库。"""
    seed_companies(db_session)
    seed_salary_benchmarks(db_session)
    seed_market_data(db_session)
    return db_session


# ======================================================================
# list_companies 缓存
# ======================================================================

class TestListCompaniesCache:
    def test_cache_miss_hits_db_and_writes_cache(self, seeded_db):
        """首次调用打 DB 并写缓存。"""
        # 确认缓存为空
        assert cache.get("companies:list:None:None:50") is None

        result, query_count = _count_queries(
            seeded_db, lambda: list_companies(seeded_db, limit=50)
        )

        # 打了 DB
        assert query_count >= 1
        assert len(result) > 0
        # 缓存已写入
        cached = cache.get("companies:list:None:None:50")
        assert cached is not None
        assert len(cached) == len(result)

    def test_cache_hit_skips_db(self, seeded_db):
        """第二次调用相同参数应直接返回缓存值，不打 DB。"""
        # 第一次调用：打 DB，写缓存
        first_result = list_companies(seeded_db, name="腾讯", limit=10)
        assert len(first_result) >= 1

        # 第二次调用：应命中缓存，不打 DB
        result, query_count = _count_queries(
            seeded_db, lambda: list_companies(seeded_db, name="腾讯", limit=10)
        )

        assert query_count == 0
        assert result == first_result

    def test_different_params_no_cache_hit(self, seeded_db):
        """不同参数不命中缓存。"""
        # 用一组参数填充缓存
        list_companies(seeded_db, name="腾讯", limit=10)

        # 用不同参数调用：应打 DB
        result, query_count = _count_queries(
            seeded_db, lambda: list_companies(seeded_db, name="阿里", limit=10)
        )

        assert query_count >= 1
        # 结果应包含阿里相关公司
        names = [c["name"] for c in result]
        assert any("阿里" in n for n in names)

    def test_different_limit_no_cache_hit(self, seeded_db):
        """不同 limit 不命中缓存。"""
        list_companies(seeded_db, limit=10)

        _, query_count = _count_queries(
            seeded_db, lambda: list_companies(seeded_db, limit=20)
        )
        assert query_count >= 1

    def test_redis_unavailable_falls_back_to_db(self, seeded_db):
        """cache.get 抛异常时应降级到直接打 DB，不抛异常。"""
        with patch.object(cache, "get", side_effect=Exception("Redis down")):
            result = list_companies(seeded_db, limit=10)
        assert len(result) > 0

    def test_cache_set_exception_does_not_raise(self, seeded_db):
        """cache.set 抛异常时函数不应抛出。"""
        with patch.object(cache, "set", side_effect=Exception("Redis down")):
            result = list_companies(seeded_db, limit=10)
        assert len(result) > 0

    def test_cache_returns_dict_not_model(self, seeded_db):
        """缓存命中后返回的是 dict（JSON 安全），而非 SQLAlchemy 模型实例。"""
        list_companies(seeded_db, limit=5)
        # 第二次命中缓存
        result = list_companies(seeded_db, limit=5)
        assert isinstance(result, list)
        assert all(isinstance(item, dict) for item in result)
        # 字段完整
        first = result[0]
        assert "id" in first
        assert "name" in first
        assert "industry" in first
        assert "size" in first


# ======================================================================
# list_salary_benchmarks 缓存
# ======================================================================

class TestListSalaryBenchmarksCache:
    def test_cache_miss_hits_db_and_writes_cache(self, seeded_db):
        """首次调用打 DB 并写缓存。"""
        assert cache.get("salary:list:None:None:None:50") is None

        result, query_count = _count_queries(
            seeded_db, lambda: list_salary_benchmarks(seeded_db, limit=50)
        )

        assert query_count >= 1
        assert len(result) > 0
        assert cache.get("salary:list:None:None:None:50") is not None

    def test_cache_hit_skips_db(self, seeded_db):
        """第二次调用相同参数应直接返回缓存值。"""
        first = list_salary_benchmarks(seeded_db, company="腾讯", limit=10)
        assert len(first) > 0

        result, query_count = _count_queries(
            seeded_db,
            lambda: list_salary_benchmarks(seeded_db, company="腾讯", limit=10),
        )
        assert query_count == 0
        assert result == first

    def test_different_params_no_cache_hit(self, seeded_db):
        """不同参数不命中缓存。"""
        list_salary_benchmarks(seeded_db, company="腾讯", limit=10)

        _, query_count = _count_queries(
            seeded_db,
            lambda: list_salary_benchmarks(seeded_db, company="阿里", limit=10),
        )
        assert query_count >= 1


# ======================================================================
# list_market_data 缓存
# ======================================================================

class TestListMarketDataCache:
    def test_cache_miss_hits_db_and_writes_cache(self, seeded_db):
        """首次调用打 DB 并写缓存。"""
        assert cache.get("market:list:None:None:None:50") is None

        result, query_count = _count_queries(
            seeded_db, lambda: list_market_data(seeded_db, limit=50)
        )

        assert query_count >= 1
        assert len(result) > 0
        assert cache.get("market:list:None:None:None:50") is not None

    def test_cache_hit_skips_db(self, seeded_db):
        """第二次调用相同参数应直接返回缓存值。"""
        first = list_market_data(seeded_db, category="salary", limit=10)
        assert len(first) > 0

        result, query_count = _count_queries(
            seeded_db,
            lambda: list_market_data(seeded_db, category="salary", limit=10),
        )
        assert query_count == 0
        assert result == first

    def test_different_params_no_cache_hit(self, seeded_db):
        """不同参数不命中缓存。"""
        list_market_data(seeded_db, category="salary", limit=10)

        _, query_count = _count_queries(
            seeded_db,
            lambda: list_market_data(seeded_db, category="employment", limit=10),
        )
        assert query_count >= 1


# ======================================================================
# Redis 降级测试（统一）
# ======================================================================

class TestRedisFallback:
    def test_cache_get_exception_does_not_raise(self, seeded_db):
        """cache.get 异常时函数不应抛出，应降级打 DB。"""
        with patch.object(cache, "get", side_effect=Exception("Redis down")):
            result = list_companies(seeded_db, limit=5)
        assert len(result) > 0

    def test_cache_set_exception_does_not_raise(self, seeded_db):
        """cache.set 异常时函数不应抛出。"""
        with patch.object(cache, "set", side_effect=Exception("Redis down")):
            result = list_market_data(seeded_db, limit=5)
        assert len(result) > 0

    def test_both_cache_ops_exception_still_returns_data(self, seeded_db):
        """cache.get 和 cache.set 都异常时仍应返回 DB 数据。"""
        with patch.object(cache, "get", side_effect=Exception("Redis down")), \
             patch.object(cache, "set", side_effect=Exception("Redis down")):
            result = list_salary_benchmarks(seeded_db, limit=5)
        assert len(result) > 0
