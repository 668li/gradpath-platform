"""缓存实现 — 支持 Redis 和内存缓存自动切换。

优先使用 Redis（如可用），自动降级到内存缓存。
支持 TTL、序列化和装饰器。
"""
import json
import logging
import time
from collections import OrderedDict
from typing import Any, Callable
from functools import wraps

from app.config import settings

logger = logging.getLogger(__name__)


class SimpleCache:
    """简单的内存缓存，支持 TTL（过期时间）和 LRU 淘汰。"""

    def __init__(self, max_size: int = 1000):
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        """获取缓存值，如果过期或不存在则返回 None。"""
        if key in self._cache:
            value, expire_time = self._cache[key]
            if time.time() < expire_time:
                self._cache.move_to_end(key)
                return value
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存值，ttl 单位为秒（默认 5 分钟）。"""
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = (value, time.time() + ttl)

    def clear(self):
        """清空所有缓存。"""
        self._cache.clear()

    def delete(self, key: str) -> bool:
        """删除指定缓存项，返回是否存在。"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def size(self) -> int:
        """返回缓存项数量。"""
        return len(self._cache)

    def keys(self) -> list[str]:
        """返回所有缓存键。"""
        return list(self._cache.keys())


class RedisCache:
    """Redis 缓存实现，自动降级到内存缓存。"""

    def __init__(self):
        self._redis = None
        self._fallback = SimpleCache()
        self._prefix = "gradpath:"
        self._init_redis()

    def _init_redis(self):
        """初始化 Redis 连接（延迟加载）。"""
        if not settings.REDIS_URL:
            logger.info("REDIS_URL 未配置，使用内存缓存")
            return

        try:
            import redis
            self._redis = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            self._redis.ping()
            logger.info("Redis 缓存已连接: %s", settings.REDIS_URL)
        except ImportError:
            logger.warning("redis-py 未安装，使用内存缓存。运行: pip install redis")
        except Exception as e:
            logger.warning("Redis 连接失败，使用内存缓存: %s", e)
            self._redis = None

    def get(self, key: str) -> Any | None:
        """获取缓存值。"""
        full_key = self._prefix + key

        if self._redis:
            try:
                data = self._redis.get(full_key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.debug("Redis GET 失败: %s", e)

        return self._fallback.get(key)

    def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存值。"""
        full_key = self._prefix + key

        if self._redis:
            try:
                serialized = json.dumps(value, ensure_ascii=False, default=str)
                self._redis.setex(full_key, ttl, serialized)
            except Exception as e:
                logger.debug("Redis SET 失败: %s", e)

        self._fallback.set(key, value, ttl)

    def clear(self):
        """清空所有缓存。"""
        if self._redis:
            try:
                keys = self._redis.keys(f"{self._prefix}*")
                if keys:
                    self._redis.delete(*keys)
            except Exception as e:
                logger.debug("Redis CLEAR 失败: %s", e)

        self._fallback.clear()

    def delete(self, key: str) -> bool:
        """删除指定缓存项。"""
        full_key = self._prefix + key
        deleted = False

        if self._redis:
            try:
                self._redis.delete(full_key)
                deleted = True
            except Exception as e:
                logger.debug("Redis DELETE 失败: %s", e)

        if self._fallback.delete(key):
            deleted = True

        return deleted

    def size(self) -> int:
        """返回缓存项数量（近似值）。"""
        if self._redis:
            try:
                return len(self._redis.keys(f"{self._prefix}*"))
            except Exception:
                pass
        return self._fallback.size()

    def keys(self) -> list[str]:
        """返回所有缓存键。"""
        if self._redis:
            try:
                keys = self._redis.keys(f"{self._prefix}*")
                return [k.replace(self._prefix, "") for k in keys]
            except Exception:
                pass
        return self._fallback.keys()


# 全局缓存实例（自动选择 Redis 或内存缓存）
cache = RedisCache()


def cached(ttl: int = 300, prefix: str = ""):
    """装饰器：为函数添加缓存支持。

    Args:
        ttl: 缓存过期时间（秒），默认 5 分钟
        prefix: 缓存键前缀，用于分组
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键：前缀 + 函数名 + 参数
            key_parts = [prefix or func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result

        wrapper.invalidate = lambda *a, **kw: cache.delete(
            ":".join([prefix or func.__name__] + [str(x) for x in a] + [f"{k}={v}" for k, v in sorted(kw.items())])
        )
        return wrapper
    return decorator
