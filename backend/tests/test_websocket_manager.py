"""WebSocket 管理器单元测试 (A8)。

覆盖：
- Redis Pub/Sub publish/subscribe 基本流程（mock redis.asyncio.Redis）
- Redis 不可用时降级到进程内广播
- 消息格式正确性（broadcast / send_to_user / broadcast_all / notify_task）
"""
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.websocket_manager import (
    ConnectionManager,
    WS_BROADCAST_CHANNEL,
)


# ----------------------------------------------------------------------
# 辅助 fixture
# ----------------------------------------------------------------------


def make_websocket():
    """构造一个 mock WebSocket，记录 send_text 调用。"""
    ws = MagicMock()
    ws.send_text = AsyncMock()
    return ws


@pytest.fixture
def manager():
    """每个测试用例使用全新的 ConnectionManager，避免全局 manager 状态污染。"""
    return ConnectionManager()


@pytest.fixture
def manager_with_redis(manager):
    """带 mock Redis 客户端的 manager。"""
    manager._redis = MagicMock()
    manager._redis.publish = AsyncMock()
    manager._main_loop = MagicMock()
    manager._main_loop.is_running.return_value = False
    return manager


# ----------------------------------------------------------------------
# publish 流程 — Redis 可用
# ----------------------------------------------------------------------


class TestPublishToRedis:
    """Redis 可用时，publish 应将消息发到 Redis channel。"""

    @pytest.mark.asyncio
    async def test_broadcast_all_publishes_to_redis(self, manager_with_redis):
        """broadcast(message) 应发布 broadcast_all 类型消息到 Redis。"""
        msg = {"type": "data_update", "items": 10}
        await manager_with_redis.broadcast(msg)

        manager_with_redis._redis.publish.assert_awaited_once()
        args = manager_with_redis._redis.publish.call_args.args
        assert args[0] == WS_BROADCAST_CHANNEL
        payload = json.loads(args[1])
        assert payload["type"] == "broadcast_all"
        assert payload["message"] == msg

    @pytest.mark.asyncio
    async def test_broadcast_to_user_publishes_send_to_user(self, manager_with_redis):
        """broadcast(message, user_id) 应发布 send_to_user 类型消息。"""
        msg = {"type": "new_notification"}
        await manager_with_redis.broadcast(msg, user_id="user-uuid-123")

        args = manager_with_redis._redis.publish.call_args.args
        payload = json.loads(args[1])
        assert payload["type"] == "send_to_user"
        assert payload["user_id"] == "user-uuid-123"
        assert payload["message"] == msg

    @pytest.mark.asyncio
    async def test_send_personal_uses_send_to_user_payload(self, manager_with_redis):
        """send_personal 应内部调用 broadcast(message, user_id)。"""
        msg = {"type": "new_notification", "title": "hi"}
        await manager_with_redis.send_personal("user-abc", msg)

        payload = json.loads(manager_with_redis._redis.publish.call_args.args[1])
        assert payload["type"] == "send_to_user"
        assert payload["user_id"] == "user-abc"
        assert payload["message"] == msg

    @pytest.mark.asyncio
    async def test_notify_task_publishes_broadcast_with_task_channel(self, manager_with_redis):
        """notify_task 应发布 broadcast 类型消息，channel = task:<task_id>。"""
        await manager_with_redis.notify_task(
            "task-xyz", "running", {"source_name": "test"}
        )

        args = manager_with_redis._redis.publish.call_args.args
        payload = json.loads(args[1])
        assert payload["type"] == "broadcast"
        assert payload["channel"] == "task:task-xyz"
        assert payload["message"]["type"] == "task_update"
        assert payload["message"]["task_id"] == "task-xyz"
        assert payload["message"]["status"] == "running"
        assert payload["message"]["data"] == {"source_name": "test"}

    @pytest.mark.asyncio
    async def test_notify_task_with_empty_data(self, manager_with_redis):
        """notify_task 不传 data 时，data 字段为空 dict。"""
        await manager_with_redis.notify_task("t1", "success")

        payload = json.loads(manager_with_redis._redis.publish.call_args.args[1])
        assert payload["message"]["data"] == {}
        assert payload["message"]["status"] == "success"


# ----------------------------------------------------------------------
# 降级流程 — Redis 不可用
# ----------------------------------------------------------------------


class TestRedisFallback:
    """Redis 不可用时，应降级为进程内分发。"""

    @pytest.mark.asyncio
    async def test_publish_without_redis_dispatches_locally(self, manager):
        """_redis = None 时，publish 直接调用 _dispatch_local。"""
        ws_a = make_websocket()
        ws_b = make_websocket()
        manager.active_connections["user-a"] = {ws_a}
        manager.active_connections["user-b"] = {ws_b}

        # broadcast_all 应分发给所有本进程连接
        await manager.broadcast({"hello": "world"})

        ws_a.send_text.assert_awaited_once()
        ws_b.send_text.assert_awaited_once()
        # 验证消息内容
        sent = json.loads(ws_a.send_text.call_args.args[0])
        assert sent == {"hello": "world"}

    @pytest.mark.asyncio
    async def test_publish_falls_back_when_redis_publish_raises(self, manager_with_redis):
        """Redis publish 抛异常时，应降级到进程内分发。"""
        manager_with_redis._redis.publish = AsyncMock(side_effect=ConnectionError("redis down"))
        ws = make_websocket()
        manager_with_redis.active_connections["user-1"] = {ws}

        await manager_with_redis.broadcast({"msg": "hi"}, user_id="user-1")

        # Redis publish 被调用但失败
        manager_with_redis._redis.publish.assert_awaited_once()
        # 本地分发仍然执行
        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args.args[0])
        assert sent == {"msg": "hi"}

    @pytest.mark.asyncio
    async def test_send_to_user_only_delivers_to_target_user(self, manager):
        """send_to_user 只分发给目标用户，不波及其他用户。"""
        ws_target = make_websocket()
        ws_other = make_websocket()
        manager.active_connections["user-target"] = {ws_target}
        manager.active_connections["user-other"] = {ws_other}

        await manager.send_personal("user-target", {"private": True})

        ws_target.send_text.assert_awaited_once()
        ws_other.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_skips_failing_websocket(self, manager):
        """WebSocket send_text 抛异常时，应从连接表移除且不影响其他连接。"""
        ws_bad = make_websocket()
        ws_bad.send_text = AsyncMock(side_effect=RuntimeError("connection closed"))
        ws_good = make_websocket()
        manager.active_connections["user-1"] = {ws_bad, ws_good}

        await manager.broadcast({"x": 1})

        ws_good.send_text.assert_awaited_once()
        # 失败的 ws 已从连接表中移除
        assert ws_bad not in manager.active_connections["user-1"]


# ----------------------------------------------------------------------
# 消息格式正确性
# ----------------------------------------------------------------------


class TestMessageFormat:
    """消息格式应符合设计规范。"""

    @pytest.mark.asyncio
    async def test_broadcast_all_payload_format(self, manager_with_redis):
        await manager_with_redis.broadcast({"k": "v"})
        payload = json.loads(manager_with_redis._redis.publish.call_args.args[1])
        assert set(payload.keys()) == {"type", "message"}
        assert payload["type"] == "broadcast_all"

    @pytest.mark.asyncio
    async def test_send_to_user_payload_format(self, manager_with_redis):
        await manager_with_redis.send_personal("uid", {"k": "v"})
        payload = json.loads(manager_with_redis._redis.publish.call_args.args[1])
        assert set(payload.keys()) == {"type", "user_id", "message"}
        assert payload["type"] == "send_to_user"
        assert payload["user_id"] == "uid"

    @pytest.mark.asyncio
    async def test_notify_task_payload_format(self, manager_with_redis):
        await manager_with_redis.notify_task("tid", "running", {"a": 1})
        payload = json.loads(manager_with_redis._redis.publish.call_args.args[1])
        assert set(payload.keys()) == {"type", "channel", "message"}
        assert payload["type"] == "broadcast"
        assert payload["channel"] == "task:tid"
        assert set(payload["message"].keys()) == {"type", "task_id", "status", "data"}
        assert payload["message"]["type"] == "task_update"

    @pytest.mark.asyncio
    async def test_publish_payload_is_json_serializable(self, manager_with_redis):
        """包含非 ASCII 字符的消息应能正确序列化。"""
        await manager_with_redis.broadcast({"text": "你好，世界"})
        raw = manager_with_redis._redis.publish.call_args.args[1]
        # ensure_ascii=False → 中文应原样存在
        assert "你好，世界" in raw
        # 应是合法 JSON
        payload = json.loads(raw)
        assert payload["message"]["text"] == "你好，世界"


# ----------------------------------------------------------------------
# 本地分发 — _dispatch_local
# ----------------------------------------------------------------------


class TestDispatchLocal:
    """_dispatch_local 应根据 payload type 路由到对应的本地分发方法。"""

    @pytest.mark.asyncio
    async def test_dispatch_send_to_user(self, manager):
        ws = make_websocket()
        manager.active_connections["uid"] = {ws}
        await manager._dispatch_local({
            "type": "send_to_user",
            "user_id": "uid",
            "message": {"a": 1},
        })
        ws.send_text.assert_awaited_once()
        assert json.loads(ws.send_text.call_args.args[0]) == {"a": 1}

    @pytest.mark.asyncio
    async def test_dispatch_broadcast_all(self, manager):
        ws1 = make_websocket()
        ws2 = make_websocket()
        manager.active_connections["u1"] = {ws1}
        manager.active_connections["u2"] = {ws2}
        await manager._dispatch_local({
            "type": "broadcast_all",
            "message": {"x": 1},
        })
        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_broadcast_task_channel_routes_to_subscribers(self, manager):
        """type=broadcast + channel=task:<id> 应分发给该任务的订阅者。"""
        ws_sub = make_websocket()
        ws_other = make_websocket()
        manager.task_subscribers["task-99"] = {ws_sub}
        manager.active_connections["user-other"] = {ws_other}

        await manager._dispatch_local({
            "type": "broadcast",
            "channel": "task:task-99",
            "message": {"status": "done"},
        })

        ws_sub.send_text.assert_awaited_once()
        # 普通用户不应收到任务频道消息
        ws_other.send_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_dispatch_broadcast_without_task_channel_falls_back_to_all(self, manager):
        """type=broadcast 但无 task: 前缀的 channel 应广播给所有人。"""
        ws1 = make_websocket()
        manager.active_connections["u1"] = {ws1}
        await manager._dispatch_local({
            "type": "broadcast",
            "channel": "other:abc",
            "message": {"x": 1},
        })
        ws1.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_unknown_type_logs_warning(self, manager, caplog):
        """未知 type 应记录 warning，不抛异常。"""
        import logging
        with caplog.at_level(logging.WARNING):
            await manager._dispatch_local({"type": "unknown_type", "message": {}})
        assert any("未知的 WebSocket 广播消息类型" in r.message for r in caplog.records)


# ----------------------------------------------------------------------
# subscribe_loop 流程
# ----------------------------------------------------------------------


class TestSubscribeLoop:
    """subscribe_loop 订阅 Redis channel 并分发消息到本进程连接。"""

    @pytest.mark.asyncio
    async def test_subscribe_loop_without_redis_url_returns_immediately(self, manager, monkeypatch):
        """REDIS_URL 未配置时，subscribe_loop 应立即返回。"""
        from app.config import settings
        monkeypatch.setattr(settings, "REDIS_URL", None)
        # 应立即返回不进入循环
        await asyncio.wait_for(manager.subscribe_loop(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_subscribe_loop_dispatches_received_messages(self, manager, monkeypatch):
        """subscribe_loop 收到 Redis 消息后应分发给本进程连接。"""
        from app.config import settings
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")

        # 准备本进程连接
        ws = make_websocket()
        manager.active_connections["uid"] = {ws}

        # 构造 mock pubsub — listen() 在 yield 完消息后让下一次 subscribe 抛 CancelledError 退出
        received_messages = [
            {
                "type": "message",
                "channel": WS_BROADCAST_CHANNEL,
                "data": json.dumps({
                    "type": "send_to_user",
                    "user_id": "uid",
                    "message": {"hello": "from-redis"},
                }),
            },
        ]

        async def listen():
            for m in received_messages:
                yield m

        subscribe_calls = {"n": 0}

        async def subscribe_side_effect(*args, **kwargs):
            subscribe_calls["n"] += 1
            if subscribe_calls["n"] >= 2:
                raise asyncio.CancelledError

        pubsub = MagicMock()
        pubsub.subscribe = AsyncMock(side_effect=subscribe_side_effect)
        pubsub.listen = listen
        pubsub.unsubscribe = AsyncMock()
        pubsub.close = AsyncMock()

        redis_client = MagicMock()
        redis_client.pubsub.return_value = pubsub

        # redis.asyncio.from_url 是同步函数（返回 Redis 实例，不是 coroutine）
        with patch("redis.asyncio.from_url", return_value=redis_client):
            try:
                await asyncio.wait_for(manager.subscribe_loop(), timeout=2.0)
            except asyncio.CancelledError:
                pass

        ws.send_text.assert_awaited_once()
        sent = json.loads(ws.send_text.call_args.args[0])
        assert sent == {"hello": "from-redis"}

    @pytest.mark.asyncio
    async def test_subscribe_loop_retries_on_failure(self, manager, monkeypatch):
        """Redis 连接失败时，subscribe_loop 应重试而不是退出。"""
        from app.config import settings
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")

        call_count = {"n": 0}

        # redis.asyncio.from_url 是同步函数；第一次抛异常，第二次返回 mock 客户端
        def fake_from_url(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ConnectionError("redis down")
            # 第二次返回一个会立即触发 CancelledError 的 mock
            pubsub = MagicMock()
            pubsub.subscribe = AsyncMock(side_effect=asyncio.CancelledError)
            pubsub.listen = MagicMock()
            pubsub.unsubscribe = AsyncMock()
            pubsub.close = AsyncMock()
            redis_client = MagicMock()
            redis_client.pubsub.return_value = pubsub
            return redis_client

        # 加速重试：替换 subscribe_loop 内的 asyncio.sleep(5) 为立即返回
        real_sleep = asyncio.sleep

        async def fast_sleep(seconds):
            await real_sleep(0)

        with patch("redis.asyncio.from_url", side_effect=fake_from_url), \
             patch("asyncio.sleep", new=fast_sleep):
            try:
                await asyncio.wait_for(manager.subscribe_loop(), timeout=2.0)
            except asyncio.CancelledError:
                pass

        # 第一次失败 → 第二次重试 → 触发 CancelledError
        assert call_count["n"] >= 2


# ----------------------------------------------------------------------
# notify_task_sync — sync 上下文调用
# ----------------------------------------------------------------------


class TestNotifyTaskSync:
    """notify_task_sync 供 sync 上下文使用，应调度 notify_task 到事件循环。"""

    def test_with_main_loop_schedules_coroutine(self, manager):
        """有主循环时，通过 run_coroutine_threadsafe 调度协程。"""
        # 使用 MagicMock 模拟正在运行的事件循环
        loop = MagicMock()
        loop.is_running.return_value = True
        manager._main_loop = loop

        async def fake_notify_task(*args, **kwargs):
            return None

        with patch.object(manager, "notify_task", return_value=fake_notify_task()) as mock_notify:
            with patch("app.core.websocket_manager.asyncio.run_coroutine_threadsafe") as mock_schedule:
                mock_schedule.return_value.add_done_callback = MagicMock()
                manager.notify_task_sync("task-1", "running", {"x": 1})
                mock_notify.assert_called_once_with("task-1", "running", {"x": 1})
                mock_schedule.assert_called_once()

    def test_without_main_loop_uses_asyncio_run(self, manager):
        """无主循环时，降级到 asyncio.run。"""
        manager._main_loop = None

        async def fake_notify_task(*args, **kwargs):
            return None

        with patch.object(manager, "notify_task", return_value=fake_notify_task()) as mock_notify, \
             patch("app.core.websocket_manager.asyncio.run") as mock_run:
            manager.notify_task_sync("task-2", "failed", {"err": "boom"})
            mock_notify.assert_called_once_with("task-2", "failed", {"err": "boom"})
            mock_run.assert_called_once()

    def test_asyncio_run_failure_is_logged_not_raised(self, manager, caplog):
        """asyncio.run 抛异常时，应记录 warning 而不是向上抛。"""
        import logging
        manager._main_loop = None

        async def fake_notify_task(*args, **kwargs):
            return None

        with patch.object(manager, "notify_task", return_value=fake_notify_task()), \
             patch("app.core.websocket_manager.asyncio.run", side_effect=RuntimeError("boom")):
            with caplog.at_level(logging.WARNING):
                # 不应抛异常
                manager.notify_task_sync("t3", "failed")
            assert any("notify_task 同步调用失败" in r.message for r in caplog.records)
