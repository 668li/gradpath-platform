# backend/app/services/ai_orchestrator.py
"""统一 LLM 入口 — 编排 AIService 与 RedisCache。

在 ``AIService`` 之上提供可选的缓存与重试能力，保持与原 ``AIService.chat``
等价的行为（未配置时抛 ``AIServiceNotConfigured``，优雅降级到内存缓存）。

B8: 集成熔断器（``AICircuitBreaker``）— 连续 5 次失败打开熔断，
30s 后半开试探。熔断打开时直接抛 ``AICircuitBreakerOpenError``，
不发送实际 LLM 请求，避免雪崩。
"""
import logging

from app.core.cache import cache
from app.services.ai_circuit_breaker import (
    AICircuitBreakerOpenError,
    ai_circuit_breaker,
)
from app.services.ai_service import AIService, AIServiceNotConfigured

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """统一 LLM 调用入口。

    - 默认 ``use_cache=False``：行为与 ``AIService.chat`` 完全等价。
    - 开启缓存时复用全局 ``RedisCache``（自动降级到内存缓存）。
    - 通过 ``AICircuitBreaker`` 包装调用，连续失败时熔断保护。
    - ``AIService.chat`` 内部已用 tenacity 重试超时/网络错误，
      因此本层的 ``retry`` 参数仅控制「整体调用」的额外重试。
    """

    def __init__(self):
        self.ai_service = AIService()
        self.cache = cache
        self.circuit_breaker = ai_circuit_breaker

    @staticmethod
    def _cache_key(system_prompt: str, user_prompt: str, timeout: int) -> str:
        return f"orch:{timeout}:{system_prompt}:{user_prompt}"

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        timeout: int = 30,
        use_cache: bool = False,
        retry: int = 1,
    ) -> str:
        """调用 LLM 并返回文本响应。

        Args:
            system_prompt: 系统提示词（角色设定 + 输出格式约束）
            user_prompt: 用户消息内容（含 context 与请求）
            timeout: 请求超时秒数，默认 30
            use_cache: 是否复用 RedisCache（默认 False，等价于原 AIService）
            retry: 调用失败时的重试次数（含首次调用），默认 1（即不重试）

        Returns:
            LLM 返回的文本

        Raises:
            AIServiceNotConfigured: LLM_API_KEY 未配置
            AICircuitBreakerOpenError: 熔断器打开时
            AIServiceRetryExhausted: tenacity 重试耗尽
            httpx.HTTPStatusError: HTTP 非 2xx
        """
        if use_cache:
            key = self._cache_key(system_prompt, user_prompt, timeout)
            cached_value = self.cache.get(key)
            if cached_value is not None:
                logger.info("AIOrchestrator 命中缓存")
                return cached_value

        last_error: Exception | None = None
        attempts = max(1, retry)
        for attempt in range(1, attempts + 1):
            try:
                # B8: 通过熔断器调用 AIService.chat
                # 熔断器打开时直接抛 AICircuitBreakerOpenError，不重试
                result = await self.circuit_breaker.call(
                    self.ai_service.chat, system_prompt, user_prompt, timeout=timeout
                )
                if use_cache:
                    self.cache.set(key, result)
                return result
            except AICircuitBreakerOpenError:
                # 熔断打开：直接向上抛，不重试
                raise
            except AIServiceNotConfigured:
                # 配置问题：直接向上抛，不重试
                raise
            except Exception as e:
                last_error = e
                logger.warning(
                    "AIOrchestrator 调用失败 (尝试 %d/%d): %s", attempt, attempts, e
                )
                if attempt >= attempts:
                    break

        assert last_error is not None
        raise last_error
