# backend/app/services/ai_circuit_breaker.py
"""B8: AI 服务熔断器 — 防止 LLM 抖动导致全站不可用。

基于 ``circuitbreaker`` 库实现，配置：
- FAILURE_THRESHOLD = 5：连续 5 次失败打开熔断
- RECOVERY_TIMEOUT = 30：30s 后进入半开状态试探

熔断打开时，所有调用直接抛出 ``AICircuitBreakerOpenError``，
不发送实际 LLM 请求，避免雪崩。

注意：``circuitbreaker`` 库的 ``CircuitBreaker`` 装饰器对 async 函数支持有限，
因此本模块采用「手动检查状态 + await 实际调用」的封装方式：
- ``call`` 方法先同步检查熔断状态，若打开则直接抛异常；
- 调用成功后通过 ``on_success`` 重置失败计数；
- 调用失败后通过 ``on_failure`` 累加失败计数。
"""
import logging
import time
from typing import Awaitable, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class AICircuitBreakerOpenError(Exception):
    """AI 熔断器打开时抛出。

    API 层捕获此异常返回 503 + "AI 服务暂时不可用，请稍后重试"。
    """

    pass


class AICircuitBreaker:
    """AI 服务熔断器（手动封装以支持 async）。

    状态机：
    - CLOSED: 正常调用，记录失败次数。失败达到 threshold 后切换到 OPEN。
    - OPEN: 拒绝所有调用，直接抛 ``AICircuitBreakerOpenError``。
      经过 ``recovery_timeout`` 秒后切换到 HALF_OPEN。
    - HALF_OPEN: 允许一次试探调用。成功则切换到 CLOSED，失败则切换回 OPEN。

    线程安全性：本类不内置锁，依赖 GIL 保证单进程下计数器读写的基本安全。
    多 worker 部署时每个进程独立计数（与限流类似），可接受。
    """

    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 30  # 秒

    def __init__(
        self,
        failure_threshold: int = FAILURE_THRESHOLD,
        recovery_timeout: int = RECOVERY_TIMEOUT,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        # 直接操作底层状态，避免装饰器模式（circuitbreaker 库对 async 支持有限）
        self._state = "closed"  # closed / open / half-open
        self._failure_count = 0
        self._opened_at: float | None = None

    @property
    def state(self) -> str:
        """当前熔断状态（closed / open / half-open）。

        注意：访问 state 会触发 open → half-open 的惰性转换
        （若已过 recovery_timeout）。
        """
        # 触发惰性状态转换：open → half-open
        if self._state == "open" and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = "half-open"
                logger.info("AI 熔断器进入半开状态，允许一次试探调用")
        return self._state

    @property
    def failure_count(self) -> int:
        """当前连续失败计数。"""
        return self._failure_count

    @property
    def is_open(self) -> bool:
        """熔断器是否处于打开状态（拒绝调用）。"""
        # 通过访问 state 属性触发惰性转换
        current = self.state
        return current == "open"

    def _before_call(self) -> None:
        """调用前检查熔断状态。打开时抛出 ``AICircuitBreakerOpenError``。"""
        if self.is_open:
            logger.warning(
                "AI 熔断器已打开，拒绝调用 (失败计数=%d)", self._failure_count
            )
            raise AICircuitBreakerOpenError(
                "AI 服务熔断器已打开，请稍后重试"
            )

    def _on_success(self) -> None:
        """调用成功：重置失败计数，关闭熔断器。"""
        if self._state != "closed":
            logger.info(
                "AI 熔断器从 %s 状态恢复到 closed", self._state
            )
        self._state = "closed"
        self._failure_count = 0
        self._opened_at = None

    def _on_failure(self) -> None:
        """调用失败：累加失败计数，达到阈值时打开熔断器。"""
        self._failure_count += 1
        if self._state == "half-open":
            # 半开状态下失败立即回到 open
            self._state = "open"
            self._opened_at = time.monotonic()
            logger.warning(
                "AI 熔断器半开试探失败，重新打开 (失败计数=%d)",
                self._failure_count,
            )
            return
        if self._failure_count >= self.failure_threshold:
            self._state = "open"
            self._opened_at = time.monotonic()
            logger.error(
                "AI 熔断器打开：连续失败 %d 次（阈值 %d），%ds 后半开试探",
                self._failure_count,
                self.failure_threshold,
                self.recovery_timeout,
            )

    async def call(self, func: Callable[..., Awaitable[T]], *args, **kwargs) -> T:
        """通过熔断器调用 async 函数。

        Args:
            func: 异步可调用对象
            *args, **kwargs: 传给 func 的参数

        Returns:
            func 的返回值

        Raises:
            AICircuitBreakerOpenError: 熔断器打开时
            Exception: func 抛出的原始异常（已计入失败计数）
        """
        self._before_call()
        try:
            result = await func(*args, **kwargs)
        except Exception as e:
            # 业务异常（如 AIServiceNotConfigured / HTTPStatusError）不应计入熔断
            # 只对网络/超时类异常计入熔断
            if _is_transient_error(e):
                self._on_failure()
            raise
        self._on_success()
        return result

    def reset(self) -> None:
        """重置熔断器到 closed 状态（主要用于测试）。"""
        self._state = "closed"
        self._failure_count = 0
        self._opened_at = None


def _is_transient_error(exc: BaseException) -> bool:
    """判断异常是否为「瞬时故障」（应计入熔断失败计数）。

    - httpx.TimeoutException / httpx.NetworkError: 网络/超时，计入
    - AIServiceRetryExhausted: 重试耗尽（底层通常是网络/超时），计入
    - httpx.HTTPStatusError: 5xx 计入（服务端抖动），4xx 不计入（客户端错误）
    - AIServiceNotConfigured: 配置问题，不计入
    - 其他异常：不计入（避免业务错误误触发熔断）
    """
    import httpx

    from app.services.ai_service import AIServiceNotConfigured, AIServiceRetryExhausted

    if isinstance(exc, AIServiceRetryExhausted):
        return True
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        # 5xx 视为服务端抖动，计入熔断；4xx 视为客户端错误，不计入
        return exc.response.status_code >= 500
    if isinstance(exc, AIServiceNotConfigured):
        return False
    return False


# 全局单例：整个进程共享一个 AI 熔断器
ai_circuit_breaker = AICircuitBreaker()
