"""WebSocket 管理器 — 实时通知支持。

多 worker 支持：通过 Redis Pub/Sub 跨进程广播。
每个 worker 维护自己的活跃连接表，通过 Redis channel `ws:broadcast` 同步消息。
Redis 不可用时降级为进程内广播（仅本 worker 用户能收到）。

消息格式（Redis channel `ws:broadcast` 上的 JSON 字符串）：
    {"type": "broadcast",     "channel": "task:123", "message": {...}}
    {"type": "broadcast_all",                                "message": {...}}
    {"type": "send_to_user",  "user_id": "uuid",       "message": {...}}
"""
import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Redis Pub/Sub channel 名称
WS_BROADCAST_CHANNEL = "ws:broadcast"


class ConnectionManager:
    """WebSocket 连接管理器，支持跨 worker 广播（Redis Pub/Sub）。"""

    def __init__(self):
        # 活跃连接 {user_id: set(websocket)}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 任务状态订阅 {task_id: set(websocket)}
        self.task_subscribers: Dict[str, Set[WebSocket]] = {}
        # Redis 异步客户端（None 表示 Redis 不可用，降级为进程内广播）
        self._redis = None
        # 主事件循环引用 — 供 sync 上下文通过 run_coroutine_threadsafe 调度协程
        self._main_loop = None

    def _update_active_websocket_gauge(self) -> None:
        """更新 prometheus ACTIVE_WEBSOCKETS 指标（A14）。

        每次连接/断开都调用，反映本进程当前活跃连接总数。
        多 worker 模式下 prometheus_client 会聚合各进程的 gauge 值。
        """
        try:
            from app.metrics import set_active_websockets
            total = sum(len(conns) for conns in self.active_connections.values())
            set_active_websockets(total)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Redis Pub/Sub 初始化与订阅
    # ------------------------------------------------------------------
    async def init_redis(self):
        """初始化 Redis Pub/Sub 客户端。

        在 FastAPI startup 事件中调用。不阻塞应用启动 —
        Redis 不可用时仅记录 warning 并降级为进程内广播。
        """
        try:
            from app.config import settings
            if not settings.REDIS_URL:
                logger.info("REDIS_URL 未配置，WebSocket 仅支持进程内广播")
                return
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            # 捕获主事件循环，供 sync 上下文调度协程
            self._main_loop = asyncio.get_running_loop()
            logger.info("WebSocket Redis Pub/Sub 客户端已初始化")
        except Exception as e:
            logger.warning("Redis 初始化失败，使用进程内广播降级: %s", e)
            self._redis = None

    async def publish(self, payload: dict):
        """将消息发布到 Redis channel，Redis 不可用时降级为进程内分发。

        Args:
            payload: 待广播的消息体（dict），需可 JSON 序列化
        """
        if self._redis is None:
            await self._dispatch_local(payload)
            return
        try:
            await self._redis.publish(
                WS_BROADCAST_CHANNEL,
                json.dumps(payload, ensure_ascii=False, default=str),
            )
        except Exception as e:
            logger.warning("Redis publish 失败，降级到进程内广播: %s", e)
            await self._dispatch_local(payload)

    async def subscribe_loop(self):
        """订阅 Redis channel，收到消息后向本进程的连接推送。

        Redis 不可用时每 5 秒重试，不阻塞应用。
        被取消时（asyncio.CancelledError）立即退出。
        """
        from app.config import settings
        if not settings.REDIS_URL:
            logger.info("REDIS_URL 未配置，subscribe_loop 不启动")
            return

        import redis.asyncio as aioredis
        while True:
            pubsub = None
            try:
                # 复用 init_redis 创建的客户端；若被重置过则新建
                if self._redis is None:
                    self._redis = aioredis.from_url(
                        settings.REDIS_URL,
                        decode_responses=True,
                        socket_connect_timeout=2,
                    )
                    self._main_loop = asyncio.get_running_loop()
                pubsub = self._redis.pubsub()
                await pubsub.subscribe(WS_BROADCAST_CHANNEL)
                logger.info(
                    "WebSocket Redis Pub/Sub 已订阅 channel=%s",
                    WS_BROADCAST_CHANNEL,
                )
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    try:
                        payload = json.loads(message["data"])
                        await self._dispatch_local(payload)
                    except Exception as e:
                        logger.warning("处理 WebSocket 广播消息失败: %s", e)
            except asyncio.CancelledError:
                logger.info("WebSocket subscribe_loop 被取消")
                raise
            except Exception as e:
                logger.warning("WebSocket subscribe_loop 异常，5 秒后重试: %s", e)
                # 重置 _redis 以触发 publish 降级，下次循环重建客户端
                self._redis = None
                await asyncio.sleep(5)
            finally:
                if pubsub is not None:
                    try:
                        await pubsub.unsubscribe(WS_BROADCAST_CHANNEL)
                        await pubsub.close()
                    except Exception:
                        pass

    # ------------------------------------------------------------------
    # 本地分发 — 把 Redis 来的消息或降级消息推送到本进程的 WebSocket
    # ------------------------------------------------------------------
    async def _dispatch_local(self, payload: dict):
        """根据 payload type 向本进程的 WebSocket 连接推送消息。"""
        msg_type = payload.get("type")
        message = payload.get("message", {})
        if msg_type == "broadcast":
            channel = payload.get("channel")
            if channel and channel.startswith("task:"):
                task_id = channel[len("task:"):]
                await self._send_to_task_subscribers(task_id, message)
            else:
                await self._send_to_all(message)
        elif msg_type == "send_to_user":
            user_id = payload.get("user_id")
            if user_id:
                await self._send_to_user_local(user_id, message)
        elif msg_type == "broadcast_all":
            await self._send_to_all(message)
        else:
            logger.warning("未知的 WebSocket 广播消息类型: %s", msg_type)

    async def _send_to_user_local(self, user_id: str, message: dict):
        data = json.dumps(message, ensure_ascii=False, default=str)
        if user_id in self.active_connections:
            for websocket in self.active_connections[user_id].copy():
                try:
                    await websocket.send_text(data)
                except Exception:
                    self.active_connections[user_id].discard(websocket)

    async def _send_to_all(self, message: dict):
        data = json.dumps(message, ensure_ascii=False, default=str)
        for uid, connections in self.active_connections.items():
            for websocket in connections.copy():
                try:
                    await websocket.send_text(data)
                except Exception:
                    connections.discard(websocket)

    async def _send_to_task_subscribers(self, task_id: str, message: dict):
        data = json.dumps(message, ensure_ascii=False, default=str)
        if task_id in self.task_subscribers:
            for websocket in self.task_subscribers[task_id].copy():
                try:
                    await websocket.send_text(data)
                except Exception:
                    self.task_subscribers[task_id].discard(websocket)

    # ------------------------------------------------------------------
    # WebSocket 连接生命周期（保持原签名）
    # ------------------------------------------------------------------
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str = "anonymous",
        subprotocol: str | None = None,
    ):
        """接受新的WebSocket连接。

        Args:
            websocket: WebSocket 实例
            user_id: 用户 ID
            subprotocol: 可选子协议（用于 FASTAPI-WS-001 子协议鉴权场景）。
                         若传入则使用该子协议 accept；否则使用默认 accept。
        """
        # 修复: FASTAPI-WS-001 配合子协议鉴权 — 调用方若已指定 subprotocol，
        # 这里用同一 subprotocol accept，避免双 accept 引发 RuntimeError。
        if subprotocol is not None:
            await websocket.accept(subprotocol=subprotocol)
        else:
            await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self._update_active_websocket_gauge()
        logger.info("WebSocket连接建立: user=%s", user_id)

    def disconnect(self, websocket: WebSocket, user_id: str = "anonymous"):
        """断开WebSocket连接。"""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        # 从任务订阅中移除
        for task_id in list(self.task_subscribers.keys()):
            self.task_subscribers[task_id].discard(websocket)
            if not self.task_subscribers[task_id]:
                del self.task_subscribers[task_id]
        self._update_active_websocket_gauge()
        logger.info("WebSocket连接断开: user=%s", user_id)

    def subscribe_task(self, websocket: WebSocket, task_id: str):
        """订阅任务状态更新。"""
        if task_id not in self.task_subscribers:
            self.task_subscribers[task_id] = set()
        self.task_subscribers[task_id].add(websocket)

    # ------------------------------------------------------------------
    # 业务广播 API（跨 worker 通过 Redis Pub/Sub）
    # ------------------------------------------------------------------
    async def broadcast(self, message: dict, user_id: str = None):
        """广播消息到所有连接或指定用户（跨 worker 通过 Redis Pub/Sub）。

        Args:
            message: 消息体
            user_id: 若指定则定向发送给该用户，否则广播给所有用户
        """
        if user_id:
            payload = {"type": "send_to_user", "user_id": user_id, "message": message}
        else:
            payload = {"type": "broadcast_all", "message": message}
        await self.publish(payload)

    async def notify_task(self, task_id: str, status: str, data: dict = None):
        """通知任务状态更新（跨 worker 通过 Redis Pub/Sub）。

        Args:
            task_id: 任务 ID
            status: 任务状态（running / success / failed / ...）
            data: 附加数据
        """
        message = {
            "type": "task_update",
            "task_id": task_id,
            "status": status,
            "data": data or {},
        }
        payload = {"type": "broadcast", "channel": f"task:{task_id}", "message": message}
        await self.publish(payload)

    async def send_personal(self, user_id: str, message: dict):
        """发送个人消息（跨 worker 通过 Redis Pub/Sub）。"""
        await self.broadcast(message, user_id)

    def _run_coroutine_sync(self, coro, label: str = "ws_coro"):
        """通用同步触发协程工具 — 供 sync 上下文使用（如 Celery worker / FastAPI BackgroundTasks 线程池）。

        通过 run_coroutine_threadsafe 将协程调度到主事件循环；
        若主循环不可用，则降级到 asyncio.run。
        异常通过 done callback 记录日志，不会抛给调用方。
        """
        if self._main_loop and self._main_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self._main_loop)

            def _log_err(fut):
                try:
                    fut.result()
                except Exception as e:
                    logger.warning("%s 异步执行失败: %s", label, e)

            future.add_done_callback(_log_err)
        else:
            try:
                asyncio.run(coro)
            except Exception as e:
                logger.warning("%s 同步调用失败: %s", label, e)

    def notify_task_sync(self, task_id: str, status: str, data: dict = None):
        """同步触发 notify_task — 供 sync 上下文使用。"""
        self._run_coroutine_sync(self.notify_task(task_id, status, data), "notify_task")

    def send_personal_sync(self, user_id: str, message: dict):
        """同步触发 send_personal — 供 sync 上下文使用（如 Celery worker）。"""
        self._run_coroutine_sync(self.send_personal(user_id, message), "send_personal")

    def broadcast_sync(self, message: dict, user_id: str | None = None):
        """同步触发 broadcast — 供 sync 上下文使用（如 Celery worker）。"""
        self._run_coroutine_sync(self.broadcast(message, user_id), "broadcast")


# 全局连接管理器
manager = ConnectionManager()
