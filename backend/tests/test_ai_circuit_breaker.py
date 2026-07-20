# backend/tests/test_ai_circuit_breaker.py
"""B8: AI 熔断器单元测试。

测试覆盖：
- 熔断器在连续 5 次失败后打开
- 熔断器打开时抛出 AICircuitBreakerOpenError
- 熔断器在 RECOVERY_TIMEOUT 后进入半开状态
- 半开状态下成功调用恢复到 closed
- 半开状态下失败回到 open
- 业务异常（AIServiceNotConfigured）不计入熔断失败计数
- HTTP 4xx 不计入熔断，5xx 计入熔断
"""
import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services.ai_circuit_breaker import (
    AICircuitBreaker,
    AICircuitBreakerOpenError,
    _is_transient_error,
)
from app.services.ai_service import (
    AIServiceNotConfigured,
    AIServiceRetryExhausted,
)


# ======================================================================
# 辅助：构造会失败的 async 函数
# ======================================================================

def _make_failing_fn(exc: Exception):
    """构造一个总是抛出指定异常的 async 函数。"""
    async def _failing(*args, **kwargs):
        raise exc
    return _failing


def _make_success_fn(retVal="ok"):
    """构造一个总是成功的 async 函数。"""
    async def _success(*args, **kwargs):
        return retVal
    return _success


# ======================================================================
# 熔断器打开：连续 5 次失败
# ======================================================================

class TestCircuitBreakerOpens:
    def test_default_config(self):
        """默认配置：FAILURE_THRESHOLD=5, RECOVERY_TIMEOUT=30。"""
        cb = AICircuitBreaker()
        assert cb.failure_threshold == 5
        assert cb.recovery_timeout == 30
        assert cb.state == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_opens_after_5_failures(self):
        """连续 5 次失败后熔断器打开。"""
        cb = AICircuitBreaker(failure_threshold=5, recovery_timeout=30)
        timeout_exc = httpx.TimeoutException("timeout")

        failing_fn = _make_failing_fn(timeout_exc)

        # 前 4 次失败：熔断器仍 closed
        for i in range(4):
            with pytest.raises(httpx.TimeoutException):
                await cb.call(failing_fn)
            assert cb.state == "closed", f"第 {i + 1} 次失败后应为 closed"
            assert cb.failure_count == i + 1

        # 第 5 次失败：熔断器打开
        with pytest.raises(httpx.TimeoutException):
            await cb.call(failing_fn)
        assert cb.state == "open"
        assert cb.failure_count == 5

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        """成功调用重置失败计数。"""
        cb = AICircuitBreaker(failure_threshold=5, recovery_timeout=30)
        timeout_exc = httpx.TimeoutException("timeout")

        # 失败 3 次
        for _ in range(3):
            with pytest.raises(httpx.TimeoutException):
                await cb.call(_make_failing_fn(timeout_exc))
        assert cb.failure_count == 3

        # 成功 1 次：重置
        result = await cb.call(_make_success_fn("ok"))
        assert result == "ok"
        assert cb.state == "closed"
        assert cb.failure_count == 0


# ======================================================================
# 熔断器打开时拒绝调用
# ======================================================================

class TestCircuitBreakerRejects:
    @pytest.mark.asyncio
    async def test_open_state_raises_error(self):
        """熔断器打开时，call 直接抛 AICircuitBreakerOpenError，不调用 func。"""
        cb = AICircuitBreaker(failure_threshold=2, recovery_timeout=30)
        timeout_exc = httpx.TimeoutException("timeout")

        # 触发熔断
        for _ in range(2):
            with pytest.raises(httpx.TimeoutException):
                await cb.call(_make_failing_fn(timeout_exc))
        assert cb.state == "open"

        # 此时调用应被拒绝
        call_count = {"n": 0}

        async def should_not_be_called():
            call_count["n"] += 1
            return "should not reach"

        with pytest.raises(AICircuitBreakerOpenError):
            await cb.call(should_not_be_called)

        assert call_count["n"] == 0, "熔断打开时不应调用 func"

    @pytest.mark.asyncio
    async def test_is_open_property(self):
        """is_open 属性正确反映熔断状态。"""
        cb = AICircuitBreaker(failure_threshold=2, recovery_timeout=30)
        assert cb.is_open is False

        # 触发熔断
        timeout_exc = httpx.TimeoutException("timeout")
        for _ in range(2):
            with pytest.raises(httpx.TimeoutException):
                await cb.call(_make_failing_fn(timeout_exc))

        assert cb.is_open is True
        assert cb.state == "open"


# ======================================================================
# 半开状态：RECOVERY_TIMEOUT 后允许一次试探
# ======================================================================

class TestCircuitBreakerHalfOpen:
    @pytest.mark.asyncio
    async def test_half_open_after_recovery_timeout(self):
        """RECOVERY_TIMEOUT 后熔断器进入半开状态，允许一次试探调用。"""
        cb = AICircuitBreaker(failure_threshold=2, recovery_timeout=1)
        timeout_exc = httpx.TimeoutException("timeout")

        # 触发熔断
        for _ in range(2):
            with pytest.raises(httpx.TimeoutException):
                await cb.call(_make_failing_fn(timeout_exc))
        assert cb.state == "open"

        # 立即调用：应被拒绝
        with pytest.raises(AICircuitBreakerOpenError):
            await cb.call(_make_success_fn())

        # 等待 RECOVERY_TIMEOUT（1s）
        time.sleep(1.1)

        # 此时 is_open 应返回 False（切换到 half-open）
        assert cb.is_open is False
        assert cb.state == "half-open"

        # 半开状态下成功调用：恢复到 closed
        result = await cb.call(_make_success_fn("recovered"))
        assert result == "recovered"
        assert cb.state == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        """半开状态下失败调用立即重新打开熔断。"""
        cb = AICircuitBreaker(failure_threshold=2, recovery_timeout=1)
        timeout_exc = httpx.TimeoutException("timeout")

        # 触发熔断
        for _ in range(2):
            with pytest.raises(httpx.TimeoutException):
                await cb.call(_make_failing_fn(timeout_exc))
        assert cb.state == "open"

        # 等待恢复
        time.sleep(1.1)
        assert cb.state == "half-open"

        # 半开状态下失败：立即回到 open
        with pytest.raises(httpx.TimeoutException):
            await cb.call(_make_failing_fn(timeout_exc))
        assert cb.state == "open"


# ======================================================================
# 异常分类：哪些异常计入熔断
# ======================================================================

class TestTransientErrorClassification:
    def test_timeout_is_transient(self):
        """httpx.TimeoutException 计入熔断。"""
        assert _is_transient_error(httpx.TimeoutException("timeout")) is True

    def test_network_error_is_transient(self):
        """httpx.NetworkError 计入熔断。"""
        assert _is_transient_error(httpx.NetworkError("network")) is True

    def test_retry_exhausted_is_transient(self):
        """AIServiceRetryExhausted 计入熔断。"""
        inner = httpx.TimeoutException("timeout")
        assert _is_transient_error(AIServiceRetryExhausted(inner)) is True

    def test_not_configured_is_not_transient(self):
        """AIServiceNotConfigured 不计入熔断（配置问题）。"""
        assert _is_transient_error(AIServiceNotConfigured("no key")) is False

    def test_5xx_is_transient(self):
        """HTTP 5xx 计入熔断（服务端抖动）。"""
        # 构造一个 5xx HTTPStatusError
        req = httpx.Request("POST", "http://example.com")
        resp = httpx.Response(500, request=req)
        exc = httpx.HTTPStatusError("5xx", request=req, response=resp)
        assert _is_transient_error(exc) is True

    def test_4xx_is_not_transient(self):
        """HTTP 4xx 不计入熔断（客户端错误）。"""
        req = httpx.Request("POST", "http://example.com")
        resp = httpx.Response(429, request=req)
        exc = httpx.HTTPStatusError("429", request=req, response=resp)
        assert _is_transient_error(exc) is False

    def test_generic_exception_not_transient(self):
        """普通异常不计入熔断（避免业务错误误触发）。"""
        assert _is_transient_error(ValueError("oops")) is False
        assert _is_transient_error(RuntimeError("oops")) is False


# ======================================================================
# 业务异常不计入熔断失败计数
# ======================================================================

class TestBusinessExceptionNotCounted:
    @pytest.mark.asyncio
    async def test_not_configured_does_not_open_circuit(self):
        """AIServiceNotConfigured 不计入熔断，连续抛出也不打开熔断。"""
        cb = AICircuitBreaker(failure_threshold=3, recovery_timeout=30)
        not_configured = AIServiceNotConfigured("no key")
        failing_fn = _make_failing_fn(not_configured)

        # 连续 5 次抛 AIServiceNotConfigured
        for _ in range(5):
            with pytest.raises(AIServiceNotConfigured):
                await cb.call(failing_fn)

        # 熔断器应仍 closed，失败计数为 0
        assert cb.state == "closed"
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_4xx_does_not_open_circuit(self):
        """HTTP 4xx 不计入熔断。"""
        cb = AICircuitBreaker(failure_threshold=3, recovery_timeout=30)
        req = httpx.Request("POST", "http://example.com")
        resp = httpx.Response(429, request=req)
        exc_4xx = httpx.HTTPStatusError("429", request=req, response=resp)
        failing_fn = _make_failing_fn(exc_4xx)

        for _ in range(5):
            with pytest.raises(httpx.HTTPStatusError):
                await cb.call(failing_fn)

        assert cb.state == "closed"
        assert cb.failure_count == 0


# ======================================================================
# reset 方法
# ======================================================================

class TestReset:
    @pytest.mark.asyncio
    async def test_reset_clears_state(self):
        """reset 方法将熔断器恢复到 closed 状态。"""
        cb = AICircuitBreaker(failure_threshold=2, recovery_timeout=30)
        timeout_exc = httpx.TimeoutException("timeout")

        # 触发熔断
        for _ in range(2):
            with pytest.raises(httpx.TimeoutException):
                await cb.call(_make_failing_fn(timeout_exc))
        assert cb.state == "open"

        cb.reset()
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.is_open is False
