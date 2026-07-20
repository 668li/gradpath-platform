"""APScheduler jobstore 配置测试（A9）。

测试 _build_scheduler_jobstore 在不同 REDIS_URL 配置下的行为：
- REDIS_URL 为空 → 使用 MemoryJobStore（开发环境）
- REDIS_URL 配置且 RedisJobStore 创建成功 → 使用 RedisJobStore（多 worker 共享）
- REDIS_URL 配置但 RedisJobStore 创建失败 → 降级到 MemoryJobStore

同时验证 slowapi Limiter 在测试环境（无 REDIS_URL）下使用内存存储，
保证 test_rate_limit.py 等限流测试可正常运行。
"""
from unittest.mock import MagicMock, patch

from apscheduler.jobstores.memory import MemoryJobStore

from app.api.crawlers import _build_scheduler_jobstore


class TestBuildSchedulerJobstore:
    def test_no_redis_url_returns_memory_jobstore(self):
        """未配置 REDIS_URL 时使用 MemoryJobStore（开发环境）。"""
        with patch("app.api.crawlers.settings") as mock_settings:
            mock_settings.REDIS_URL = None
            store = _build_scheduler_jobstore()
        assert isinstance(store, MemoryJobStore)

    def test_empty_redis_url_returns_memory_jobstore(self):
        """REDIS_URL 为空字符串时使用 MemoryJobStore。"""
        with patch("app.api.crawlers.settings") as mock_settings:
            mock_settings.REDIS_URL = ""
            store = _build_scheduler_jobstore()
        assert isinstance(store, MemoryJobStore)

    def test_redis_url_returns_redis_jobstore(self):
        """REDIS_URL 配置正确时使用 RedisJobStore，并正确解析 host/port/password/db。"""
        with patch("app.api.crawlers.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://:password@localhost:6379/0"
            with patch(
                "apscheduler.jobstores.redis.RedisJobStore"
            ) as mock_redis_cls:
                mock_store = MagicMock()
                mock_redis_cls.return_value = mock_store
                store = _build_scheduler_jobstore()
        # 验证使用 RedisJobStore 且参数解析正确
        mock_redis_cls.assert_called_once()
        kwargs = mock_redis_cls.call_args.kwargs
        assert kwargs["host"] == "localhost"
        assert kwargs["port"] == 6379
        assert kwargs["password"] == "password"
        assert kwargs["db"] == 0
        assert store is mock_store

    def test_redis_unavailable_falls_back_to_memory(self):
        """REDIS_URL 配置但 RedisJobStore 创建失败（如 Redis 不可达）时
        降级到 MemoryJobStore，不抛异常。"""
        with patch("app.api.crawlers.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6379/0"
            with patch(
                "apscheduler.jobstores.redis.RedisJobStore",
                side_effect=Exception("connection refused"),
            ):
                store = _build_scheduler_jobstore()
        assert isinstance(store, MemoryJobStore)

    def test_redis_url_with_custom_db_and_port(self):
        """REDIS_URL 指定自定义端口和 db index 时正确解析。"""
        with patch("app.api.crawlers.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost:6380/3"
            with patch(
                "apscheduler.jobstores.redis.RedisJobStore"
            ) as mock_redis_cls:
                _build_scheduler_jobstore()
        kwargs = mock_redis_cls.call_args.kwargs
        assert kwargs["port"] == 6380
        assert kwargs["db"] == 3
        assert kwargs["password"] is None

    def test_redis_url_default_port_when_not_specified(self):
        """REDIS_URL 未指定端口时使用默认 6379。"""
        with patch("app.api.crawlers.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost/0"
            with patch(
                "apscheduler.jobstores.redis.RedisJobStore"
            ) as mock_redis_cls:
                _build_scheduler_jobstore()
        kwargs = mock_redis_cls.call_args.kwargs
        assert kwargs["port"] == 6379

    def test_redis_url_default_db_when_not_specified(self):
        """REDIS_URL 未指定 db index 时使用默认 0。"""
        with patch("app.api.crawlers.settings") as mock_settings:
            mock_settings.REDIS_URL = "redis://localhost"
            with patch(
                "apscheduler.jobstores.redis.RedisJobStore"
            ) as mock_redis_cls:
                _build_scheduler_jobstore()
        kwargs = mock_redis_cls.call_args.kwargs
        assert kwargs["db"] == 0


class TestLimiterStorageFallback:
    """验证 slowapi Limiter 在无 Redis 时降级到内存存储，
    保证 test_rate_limit.py 的限流测试可正常运行。"""

    def test_limiter_uses_memory_storage_in_test_env(self):
        """测试环境无 REDIS_URL，limiter 使用 memory:// 存储后端。"""
        from app.main import limiter
        # slowapi Limiter 将 storage_uri 保存在 _storage_uri 属性
        # （其底层存储为 limits.storage.Storage 实例）
        # 在测试环境中 REDIS_URL 未配置，应使用内存存储
        assert limiter._storage_uri == "memory://"

    def test_limiter_has_reset_method(self):
        """limiter.reset() 在内存存储下应可正常调用（conftest 依赖此方法）。"""
        from app.main import limiter
        # 不抛异常即可
        limiter.reset()
