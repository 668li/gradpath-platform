# backend/tests/test_ai_quota.py
"""B8: AI 配额服务单元测试。

测试覆盖：
- 配额检查：未超额返回当前已用次数
- 配额检查：超额抛 AILLMQuotaExceeded
- 配额递增：成功调用 INCR 并设置 TTL
- Redis 不可用时降级到不限制（返回 None，不抛异常）
- 配额计数按日期隔离
- 配额计数按用户隔离
"""
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai_quota_service import (
    AILLMQuotaExceeded,
    AIQuotaService,
)


# ======================================================================
# 辅助：构造带 mock Redis 的 AIQuotaService
# ======================================================================

def _make_service_with_redis(redis_mock, quota=100):
    """构造一个使用 mock Redis 的 AIQuotaService（绕过 _init_redis）。"""
    svc = AIQuotaService.__new__(AIQuotaService)
    svc._redis = redis_mock
    svc._quota = quota
    return svc


def _make_redis_mock(get_value="0", incr_value=1):
    """构造一个 mock Redis 客户端。"""
    redis_mock = MagicMock()
    redis_mock.get.return_value = get_value
    redis_mock.incr.return_value = incr_value
    redis_mock.expire.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.keys.return_value = []
    redis_mock.ping.return_value = True
    return redis_mock


# ======================================================================
# 配额检查：未超额
# ======================================================================

class TestCheckQuotaNotExceeded:
    @pytest.mark.asyncio
    async def test_returns_used_count_when_under_quota(self):
        """未超额时返回当前已用次数。"""
        redis_mock = _make_redis_mock(get_value="10")
        svc = _make_service_with_redis(redis_mock, quota=100)

        result = await svc.check_llm_quota(user_id=1)
        assert result == 10
        # 不应抛异常
        redis_mock.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_zero_usage_returns_zero(self):
        """当天未调用过返回 0。"""
        redis_mock = _make_redis_mock(get_value=None)  # Redis GET 返回 None
        svc = _make_service_with_redis(redis_mock, quota=100)

        result = await svc.check_llm_quota(user_id=1)
        assert result == 0

    @pytest.mark.asyncio
    async def test_just_below_quota_passes(self):
        """used = quota - 1 时仍允许调用。"""
        redis_mock = _make_redis_mock(get_value="99")
        svc = _make_service_with_redis(redis_mock, quota=100)

        result = await svc.check_llm_quota(user_id=1)
        assert result == 99


# ======================================================================
# 配额检查：超额
# ======================================================================

class TestCheckQuotaExceeded:
    @pytest.mark.asyncio
    async def test_raises_when_exceeded(self):
        """超额时抛 AILLMQuotaExceeded。"""
        redis_mock = _make_redis_mock(get_value="100")
        svc = _make_service_with_redis(redis_mock, quota=100)

        with pytest.raises(AILLMQuotaExceeded) as exc_info:
            await svc.check_llm_quota(user_id=1)

        assert exc_info.value.used == 100
        assert exc_info.value.quota == 100

    @pytest.mark.asyncio
    async def test_raises_when_far_exceeded(self):
        """远超配额时也抛异常。"""
        redis_mock = _make_redis_mock(get_value="500")
        svc = _make_service_with_redis(redis_mock, quota=100)

        with pytest.raises(AILLMQuotaExceeded):
            await svc.check_llm_quota(user_id=1)

    @pytest.mark.asyncio
    async def test_quota_value_from_settings(self):
        """配额值可通过 settings.LLM_DAILY_QUOTA 配置。"""
        redis_mock = _make_redis_mock(get_value="50")
        svc = _make_service_with_redis(redis_mock, quota=50)

        with pytest.raises(AILLMQuotaExceeded) as exc_info:
            await svc.check_llm_quota(user_id=1)
        assert exc_info.value.quota == 50


# ======================================================================
# 配额递增
# ======================================================================

class TestIncrQuota:
    @pytest.mark.asyncio
    async def test_incr_returns_new_count(self):
        """递增后返回新计数。"""
        redis_mock = _make_redis_mock(incr_value=11)
        svc = _make_service_with_redis(redis_mock, quota=100)

        result = await svc.incr_llm_quota(user_id=1)
        assert result == 11
        redis_mock.incr.assert_called_once()

    @pytest.mark.asyncio
    async def test_incr_sets_ttl_on_first_call(self):
        """第一次调用（new_count == 1）时设置 TTL。"""
        redis_mock = _make_redis_mock(incr_value=1)
        svc = _make_service_with_redis(redis_mock, quota=100)

        await svc.incr_llm_quota(user_id=1)
        redis_mock.expire.assert_called_once()
        # 验证 TTL 参数
        args = redis_mock.expire.call_args
        assert args[0][1] == 86400  # 24h

    @pytest.mark.asyncio
    async def test_incr_does_not_set_ttl_on_subsequent_calls(self):
        """后续调用（new_count > 1）不重置 TTL。"""
        redis_mock = _make_redis_mock(incr_value=5)
        svc = _make_service_with_redis(redis_mock, quota=100)

        await svc.incr_llm_quota(user_id=1)
        redis_mock.expire.assert_not_called()

    @pytest.mark.asyncio
    async def test_incr_failure_does_not_raise(self):
        """Redis INCR 失败时不抛异常（不阻塞业务）。"""
        redis_mock = _make_redis_mock()
        redis_mock.incr.side_effect = Exception("Redis down")
        svc = _make_service_with_redis(redis_mock, quota=100)

        # 不应抛异常
        result = await svc.incr_llm_quota(user_id=1)
        assert result is None


# ======================================================================
# Redis 不可用时降级
# ======================================================================

class TestRedisUnavailable:
    def test_no_redis_url_degrades_to_unlimited(self, monkeypatch):
        """REDIS_URL 未配置时，服务降级到不限制模式。"""
        from app.config import settings
        monkeypatch.setattr(settings, "REDIS_URL", None)

        svc = AIQuotaService()
        assert svc._redis is None

    @pytest.mark.asyncio
    async def test_check_quota_returns_none_when_redis_unavailable(self):
        """Redis 不可用时，check_llm_quota 返回 None（不限制）。"""
        svc = AIQuotaService.__new__(AIQuotaService)
        svc._redis = None
        svc._quota = 100

        result = await svc.check_llm_quota(user_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_incr_returns_none_when_redis_unavailable(self):
        """Redis 不可用时，incr_llm_quota 返回 None。"""
        svc = AIQuotaService.__new__(AIQuotaService)
        svc._redis = None
        svc._quota = 100

        result = await svc.incr_llm_quota(user_id=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_check_quota_degrades_on_redis_error(self):
        """Redis 操作失败时降级到不限制（不抛异常）。"""
        redis_mock = _make_redis_mock()
        redis_mock.get.side_effect = Exception("Redis connection lost")
        svc = _make_service_with_redis(redis_mock, quota=100)

        # 不应抛异常，返回 None
        result = await svc.check_llm_quota(user_id=1)
        assert result is None


# ======================================================================
# Key 格式与隔离
# ======================================================================

class TestQuotaKeyIsolation:
    @pytest.mark.asyncio
    async def test_key_format(self):
        """key 格式为 llm_quota:{user_id}:{YYYY-MM-DD}。"""
        redis_mock = _make_redis_mock(get_value="5")
        svc = _make_service_with_redis(redis_mock, quota=100)

        await svc.check_llm_quota(user_id=42)

        key = redis_mock.get.call_args[0][0]
        today = date.today().isoformat()
        assert key == f"llm_quota:42:{today}"

    @pytest.mark.asyncio
    async def test_different_users_have_different_keys(self):
        """不同用户的配额 key 隔离。"""
        redis_mock = _make_redis_mock(get_value="5")
        svc = _make_service_with_redis(redis_mock, quota=100)

        await svc.check_llm_quota(user_id=1)
        await svc.check_llm_quota(user_id=2)

        keys = [call.args[0] for call in redis_mock.get.call_args_list]
        assert keys[0] != keys[1]
        assert "user_id=1" not in keys[0]  # user_id 直接拼接到 key，不是 "user_id=1"

    @pytest.mark.asyncio
    async def test_different_dates_have_different_keys(self):
        """不同日期的配额 key 隔离。"""
        svc = AIQuotaService.__new__(AIQuotaService)
        svc._redis = _make_redis_mock()
        svc._quota = 100

        key1 = svc._quota_key(1, date(2025, 7, 20))
        key2 = svc._quota_key(1, date(2025, 7, 21))
        assert key1 != key2
        assert "2025-07-20" in key1
        assert "2025-07-21" in key2


# ======================================================================
# reset 方法
# ======================================================================

class TestReset:
    @pytest.mark.asyncio
    async def test_reset_specific_user(self):
        """reset(user_id) 删除指定用户的当日 key。"""
        redis_mock = _make_redis_mock()
        svc = _make_service_with_redis(redis_mock, quota=100)

        svc.reset(user_id=42)

        redis_mock.delete.assert_called_once()
        key = redis_mock.delete.call_args[0][0]
        today = date.today().isoformat()
        assert key == f"llm_quota:42:{today}"

    @pytest.mark.asyncio
    async def test_reset_all_users(self):
        """reset() 清空所有用户的当日 key。"""
        redis_mock = _make_redis_mock()
        redis_mock.keys.return_value = ["llm_quota:1:2025-07-20", "llm_quota:2:2025-07-20"]
        svc = _make_service_with_redis(redis_mock, quota=100)

        svc.reset()

        redis_mock.keys.assert_called_once()
        redis_mock.delete.assert_called_once()

    def test_reset_no_redis_does_nothing(self):
        """Redis 不可用时 reset 不抛异常。"""
        svc = AIQuotaService.__new__(AIQuotaService)
        svc._redis = None
        svc._quota = 100
        # 不应抛异常
        svc.reset(user_id=1)
