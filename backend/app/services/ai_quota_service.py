# backend/app/services/ai_quota_service.py
"""B8: 每用户 LLM 调用日预算 — 防止恶意用户并发打 AI 端点消耗额度。

设计：
- 用 Redis 计数器：key 格式 ``llm_quota:{user_id}:{date}``，TTL=86400s
- 默认预算：100 次/天/用户（可通过 ``settings.LLM_DAILY_QUOTA`` 配置）
- 超额抛出 ``AILLMQuotaExceeded`` 异常，API 层返回 429
- Redis 不可用时降级到不限制（避免阻塞业务）

接口：
- ``check_llm_quota(user_id)``: 检查配额，超额抛异常，否则返回 None
- ``incr_llm_quota(user_id)``: 递增当日调用计数
- ``get_llm_quota(user_id)``: 查询当日已用次数（主要用于测试/调试）

注意：本服务使用独立的 Redis 客户端（与 cache 模块隔离），
因为配额计数需要原子性 INCR + EXPIRE，不能复用 RedisCache 的 JSON 序列化。
"""

import logging
from datetime import date

from app.config import settings
from app.utils.business_time import beijing_today

logger = logging.getLogger(__name__)


class AILLMQuotaExceeded(Exception):
    """LLM 日配额超额时抛出。

    API 层捕获此异常返回 429 + "今日 AI 调用次数已达上限"。
    """

    def __init__(self, used: int, quota: int):
        self.used = used
        self.quota = quota
        super().__init__(f"今日 AI 调用次数已达上限 (used={used}, quota={quota})")


class AIQuotaService:
    """每用户 LLM 日预算服务。

    使用 Redis INCR + EXPIRE 实现原子计数。Redis 不可用时降级到不限制，
    保证业务可用性（宁可放过也不阻塞）。
    """

    KEY_PREFIX = "llm_quota"
    KEY_TTL = 86400  # 1 天（秒）

    def __init__(self):
        self._redis = None
        self._quota = settings.LLM_DAILY_QUOTA
        self._init_redis()

    def _init_redis(self):
        """初始化 Redis 连接（延迟加载，与 cache 模块独立）。"""
        if not settings.REDIS_URL:
            logger.info("AI 配额服务：REDIS_URL 未配置，降级到不限制模式")
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
            logger.info("AI 配额服务 Redis 已连接: %s", settings.REDIS_URL)
        except ImportError:
            logger.warning("AI 配额服务：redis-py 未安装，降级到不限制模式")
            self._redis = None
        except Exception as e:
            logger.warning("AI 配额服务：Redis 连接失败，降级到不限制模式: %s", e)
            self._redis = None

    def _quota_key(self, user_id, today: date | None = None) -> str:
        """构造配额计数 key: ``llm_quota:{user_id}:{YYYY-MM-DD}``"""
        d = today or beijing_today()
        return f"{self.KEY_PREFIX}:{user_id}:{d.isoformat()}"

    _CONSUME_SCRIPT = """
local current = tonumber(redis.call("GET", KEYS[1]) or "0")
local quota = tonumber(ARGV[1])
if current >= quota then
    return -1
end
local next_count = redis.call("INCR", KEYS[1])
if next_count == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[2])
end
return next_count
"""

    async def consume_llm_quota(self, user_id) -> int | None:
        """Atomically reserve one LLM call from the user's daily budget.

        The old check-then-increment sequence allowed concurrent requests to
        observe the same remaining slot and overshoot the daily quota.
        """
        if self._redis is None:
            return None

        key = self._quota_key(user_id)
        try:
            result = self._redis.eval(
                self._CONSUME_SCRIPT,
                1,
                key,
                self._quota,
                self.KEY_TTL,
            )
        except Exception as e:
            logger.warning("AI 配额消费失败，降级到不限制: %s", e)
            return None

        if int(result) == -1:
            raise AILLMQuotaExceeded(used=self._quota, quota=self._quota)

        return int(result)

    async def incr_llm_quota(self, user_id) -> int | None:
        """Legacy counter increment kept for compatibility.

        New request paths must use consume_llm_quota(); this method is not a
        quota admission check and should not be used to authorize an AI call.
        """
        if self._redis is None:
            return None
        key = self._quota_key(user_id)
        try:
            new_count = self._redis.incr(key)
            if new_count == 1:
                self._redis.expire(key, self.KEY_TTL)
            return new_count
        except Exception as e:
            logger.warning("AI 配额递增失败: %s", e)
            return None

    async def get_llm_quota(self, user_id) -> int | None:
        """查询用户当日已用次数（主要用于测试/调试）。"""
        if self._redis is None:
            return None
        key = self._quota_key(user_id)
        try:
            return int(self._redis.get(key) or 0)
        except Exception as e:
            logger.warning("AI 配额查询失败: %s", e)
            return None

    def reset(self, user_id=None, today: date | None = None) -> None:
        """重置配额计数（主要用于测试）。

        Args:
            user_id: 指定用户 ID；None 时清空所有用户
            today: 指定日期；None 时使用今天
        """
        if self._redis is None:
            return
        try:
            if user_id is not None:
                key = self._quota_key(user_id, today)
                self._redis.delete(key)
            else:
                # 清空所有用户的当日配额
                d = today or beijing_today()
                pattern = f"{self.KEY_PREFIX}:*:{d.isoformat()}"
                batch: list[str] = []
                for key in self._redis.scan_iter(match=pattern, count=500):
                    batch.append(key)
                    if len(batch) >= 500:
                        self._redis.delete(*batch)
                        batch.clear()
                if batch:
                    self._redis.delete(*batch)
        except Exception as e:
            logger.warning("AI 配额重置失败: %s", e)


# 全局单例
ai_quota_service = AIQuotaService()


# 便捷函数（供 API 层调用）
async def consume_llm_quota(user_id):
    """原子地预留一次 LLM 调用额度。"""
    return await ai_quota_service.consume_llm_quota(user_id)


async def check_llm_quota(user_id):
    """检查用户当日 LLM 配额（仅查询，不预留额度）。"""
    return await ai_quota_service.check_llm_quota(user_id)


async def incr_llm_quota(user_id):
    """递增用户当日 LLM 调用计数。"""
    return await ai_quota_service.incr_llm_quota(user_id)
