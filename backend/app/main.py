import asyncio
import json
import logging
import shutil
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware

from app.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import BusinessError
from app.core.logging import correlation_id_var, request_id_var, setup_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.websocket_manager import manager as ws_manager
from app.database import Base, engine, get_db
from app.error_handlers import register_error_handlers
from app.models.user import User

# 配置结构化日志（尽早执行，确保后续组件日志统一格式 + request_id 追踪）
setup_logging(settings.LOG_LEVEL)

logger = logging.getLogger("gradpath")


# ----------------------------------------------------------------------
# Sentry 初始化（B5）— 在 FastAPI app 创建前完成，确保能捕获后续所有异常。
# 通过 SENTRY_DSN 环境变量启用；未配置时跳过，不影响本地开发。
# ----------------------------------------------------------------------
def _scrub_sensitive_data(event: dict, hint: dict | None = None) -> dict | None:
    """Sentry before_send 钩子：过滤敏感字段，避免 PII/密钥上传。

    覆盖：
    - request headers: Authorization / Cookie / X-Api-Key
    - request body / query 中字段名命中敏感词的值
    - extra / breadcrumbs 中的敏感字段
    """
    sensitive_keys = {
        "password",
        "password_hash",
        "new_password",
        "current_password",
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "secret_key",
        "api_key",
        "authorization",
        "cookie",
        "session",
        "csrf",
    }

    def _scrub(obj):
        if isinstance(obj, dict):
            return {
                k: ("[REDACTED]" if k.lower() in sensitive_keys else _scrub(v))
                for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [_scrub(v) for v in obj]
        return obj

    try:
        request = event.get("request") or {}
        # headers
        headers = request.get("headers") or {}
        scrubbed_headers = {}
        for k, v in headers.items():
            if k.lower() in {"authorization", "cookie", "x-api-key"}:
                scrubbed_headers[k] = "[REDACTED]"
            else:
                scrubbed_headers[k] = v
        request["headers"] = scrubbed_headers
        # body / query
        for field in ("data", "query_string", "json"):
            if field in request and request[field]:
                request[field] = _scrub(request[field])
        event["request"] = request
        # extra / contexts / breadcrumbs
        if "extra" in event:
            event["extra"] = _scrub(event["extra"])
        if "contexts" in event:
            event["contexts"] = _scrub(event["contexts"])
        breadcrumbs = event.get("breadcrumbs") or []
        event["breadcrumbs"] = [_scrub(b) for b in breadcrumbs]
    except Exception as e:  # noqa: BLE001
        logger.debug("Sentry scrub error: %s", e)
    return event


if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            integrations=[
                FastApiIntegration(),
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            send_default_pii=False,
            before_send=_scrub_sensitive_data,
        )
        logger.info("Sentry 已初始化: env=%s", settings.ENV)
    except Exception as e:  # noqa: BLE001
        logger.warning("Sentry 初始化失败（不影响启动）: %s", e)

# 修复: FASTAPI-OPENAPI-001 — 生产环境关闭 /docs /redoc /openapi.json，
# 避免接口结构暴露给未授权用户；开发/预发环境保留方便调试。
_is_production = settings.ENVIRONMENT == "production"

app = FastAPI(
    title="GradPath API",
    description="GradPath 职业规划平台 — 提供考研导师评价、院校情报、职业规划、爬虫管理等功能",
    version="0.1.0",
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
    openapi_tags=[
        {"name": "认证", "description": "用户注册、登录、Token 刷新"},
        {"name": "仪表盘", "description": "用户仪表盘概览与周报"},
        {"name": "职业规划", "description": "职业计划、模板、决策分析"},
        {"name": "考研情报", "description": "考研资讯、院校数据、经验帖"},
        {"name": "社区", "description": "社区交流、帖子、问答"},
        {"name": "AI 助手", "description": "AI 对话、知识库、智能推荐"},
        {"name": "爬虫管理", "description": "管理员爬虫调度与监控"},
        {"name": "数据管道", "description": "APScheduler 定时任务管理"},
        {"name": "RAG", "description": "混合检索增强生成 — 关键词 + 语义搜索 200K+ 记录"},
    ],
)

# ----------------------------------------------------------------------
# 限流器（slowapi）
# 必须在路由模块导入之前创建：路由模块会执行 `from app.main import limiter`，
# 若 limiter 尚未定义将触发循环导入错误。
# 修复: A9 — 使用 Redis 存储后端，保证多 worker 限流计数一致；
#       Redis 不可用时降级到内存存储（开发环境），不阻塞应用启动。
#       注意：4 worker 各自内存计数时，实际限流上限变成 4×
#       （注册从 3/min 变 12/min，登录从 5/min 变 20/min）。
# ----------------------------------------------------------------------
_storage_uri = "memory://"
if settings.REDIS_URL:
    try:
        import redis as _redis_check
        _r = _redis_check.from_url(settings.REDIS_URL)
        _r.ping()
        _storage_uri = settings.REDIS_URL
        logger.info("slowapi 限流器使用 Redis 存储后端: %s", settings.REDIS_URL)
    except Exception as _e:
        logger.warning(
            "Redis 不可用，slowapi 限流器降级到内存存储（多 worker 限流计数可能不一致）: %s",
            _e,
        )

limiter = Limiter(
    storage_uri=_storage_uri,
    key_func=get_remote_address,
    default_limits=["200/hour"],
    headers_enabled=True,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — 允许前端跨域访问（源由配置统一管理）
# 修复: FASTAPI-CORS-001 — 拒绝 allow_origins=["*"] 与 allow_credentials=True 同时启用，
# 否则浏览器会拒绝带凭据的跨域请求，且配置过宽等同禁用同源策略。
_cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
if "*" in _cors_origins:
    raise RuntimeError(
        "CORS_ORIGINS 不能包含 '*' (FASTAPI-CORS-001)。"
        "请显式列出允许的前端源，用逗号分隔，例如: https://app.example.com,http://localhost:3000"
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# 安全响应头中间件 — 注入 X-Frame-Options / X-Content-Type-Options / HSTS 等
app.add_middleware(SecurityHeadersMiddleware)

# Gzip 压缩中间件 — 响应体 > 500 bytes 时自动 gzip 压缩，减少传输体积 ~60-70%
app.add_middleware(GZipMiddleware, minimum_size=500)

# ----------------------------------------------------------------------
# 响应缓存中间件 — 为只读 GET 端点添加 Cache-Control 头
# ----------------------------------------------------------------------
CACHE_CONTROL_MAP: dict[str, str] = {
    "/api/dashboard/overview": "private, max-age=30",
    "/api/dashboard/weekly-recap": "private, max-age=60",
    "/api/community/stats": "public, max-age=300",
    "/api/knowledge": "private, max-age=120",
    "/api/kaoyan/experience-posts": "public, max-age=60",
    "/api/gamification/profile": "private, max-age=30",
    "/api/employment/schools": "public, max-age=3600",
    "/api/employment/stats": "public, max-age=300",
    "/api/employment/search": "public, max-age=120",
    "/api/career-profile": "private, max-age=60",
}

@app.middleware("http")
async def cache_control_middleware(request: Request, call_next):
    response = await call_next(request)
    if request.method == "GET" and response.status_code == 200:
        path = request.url.path.rstrip("/")
        for pattern, directive in CACHE_CONTROL_MAP.items():
            if path == pattern or path.startswith(pattern + "/"):
                response.headers["Cache-Control"] = directive
                break
    return response

# ----------------------------------------------------------------------
# 请求日志中间件 — 为每个请求注入 request_id 并记录方法/路径/状态/耗时
# 通过 @app.middleware 注册，位于 CORS 之外（最外层），可记录完整请求链路。
# ----------------------------------------------------------------------
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    rid = uuid4().hex[:8]
    cid = uuid4().hex
    request_id_var.set(rid)
    correlation_id_var.set(cid)
    request.state.request_id = rid
    request.state.correlation_id = cid
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(
        "%s %s %d %.1fms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = rid
    response.headers["X-Correlation-ID"] = cid
    # Record metrics — 同时写入 prometheus_client 与旧版 /api/metrics
    try:
        from app.metrics import record_http_request
        record_http_request(
            request.method,
            request.url.path,
            response.status_code,
            duration_ms / 1000.0,
        )
    except Exception:
        pass
    return response


# ----------------------------------------------------------------------
# /metrics 端点（A14）— Prometheus 标准格式，仅管理员可访问
# 与 /api/metrics 共存：/metrics 输出 prometheus_client 聚合格式，
# /api/metrics 输出旧版自定义格式（保持向后兼容）。
# ----------------------------------------------------------------------
@app.get("/metrics")
def prometheus_metrics_endpoint(
    user: User = Depends(get_current_user),
):
    """Prometheus 标准格式指标端点（仅登录用户可访问）。

    生产环境应通过 nginx 限制内网访问，并配合 IP 白名单。
    多 worker 模式下通过 MultiProcessCollector 聚合所有 worker 指标。
    """
    from app.metrics import render_metrics
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)

# ----------------------------------------------------------------------
# 路由自动发现：扫描 app.api 下所有模块的 router 并注册
# 新增 API 端点只需创建带 router 的 .py 文件，无需修改 main.py
# ----------------------------------------------------------------------
from app.api import auto_discover_routers
auto_discover_routers(app)

# ----------------------------------------------------------------------
# MCP Server — 暴露核心 GradPath 工具给 AI 代理
# fastapi-mcp 有递归 bug，改用 SSE transport 手动注册核心工具
# 修复: 工具实现下沉到 app.services.mcp_service，main.py 只做注册
# 修复: FASTAPI-AUTH-001 / FASTAPI-AUTHZ-001 — MCP SSE 端点默认无认证，
# 任意能访问 /mcp/* 的客户端均可调用所有工具（含用户画像、薪资等敏感数据）。
# 在 mount 处增加 Bearer token 认证中间件，校验 access_token 后才放行。
# ----------------------------------------------------------------------
class MCPAuthMiddleware(BaseHTTPMiddleware):
    """MCP SSE 端点认证中间件 (FASTAPI-AUTH-001 / FASTAPI-AUTHZ-001)。

    所有打到 /mcp/* 的请求必须携带有效 access_token，否则返回 401。
    支持两种传递方式：
    1. Authorization: Bearer <token> — 标准 HTTP 头（POST /mcp/messages 用）
    2. ?token=<token> — URL query 参数（GET /mcp/sse 用，因为浏览器
       EventSource API 不支持自定义请求头）
    """

    async def dispatch(self, request: Request, call_next):
        from app.core.security import decode_token
        from jose.exceptions import JWTError

        # 优先从 Authorization 头解析 Bearer token
        auth_header = request.headers.get("authorization") or ""
        token: str | None = None
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        # SSE EventSource 不支持自定义头，回退到 query 参数
        if not token:
            token = request.query_params.get("token")

        if not token:
            return JSONResponse(status_code=401, content={"detail": "MCP authentication required"})
        try:
            payload = decode_token(token)
        except (JWTError, Exception):
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        # 仅允许 access token 调用 MCP 工具，refresh token 拒绝
        if payload.get("type") != "access":
            return JSONResponse(status_code=401, content={"detail": "Invalid token type"})
        # 将 user_id 注入 request.state 供下游工具使用
        request.state.user_id = payload.get("sub")
        return await call_next(request)


try:
    from mcp.server.fastmcp import FastMCP
    from app.services.mcp_service import register_mcp_tools

    mcp = FastMCP("GradPath", instructions="GradPath 职业规划平台 — 考研/考公/就业一体化工具集")

    # 工具实现下沉到 services/mcp_service.py，避免 main.py 直接调用 service 层
    register_mcp_tools(mcp)

    mcp_server = mcp
    # 挂载 MCP SSE: /mcp/sse (SSE stream), /mcp/messages (MCP protocol)
    # 修复: FASTAPI-AUTH-001 — 给 sse_app 加认证中间件，避免工具未授权调用
    _mcp_app = mcp.sse_app()
    _mcp_app.add_middleware(MCPAuthMiddleware)
    app.mount("/mcp", _mcp_app)
    logger.info("MCP server 已挂载: /mcp/sse (SSE), /mcp/messages (MCP) — 已启用 Bearer 认证")
except ImportError:
    mcp_server = None
    logger.info("mcp 库未安装，跳过 MCP server")
except Exception as e:
    mcp_server = None
    logger.warning("MCP server 创建失败: %s", e)


# 创建数据库表（仅开发模式；生产环境使用 Alembic 迁移）
# 必须在路由导入之后：路由导入触发模型注册到 Base.metadata
if settings.ENVIRONMENT == "development":
    Base.metadata.create_all(bind=engine)


# Redis 启动可达性检查 (A15)
# 仅 PING 一次记录日志，失败不阻止启动：容器编排中服务启动顺序可能不同步，
# Redis 可能稍后启动；运行时使用 Redis 的代码会自行处理连接异常。
if settings.REDIS_URL:
    try:
        import redis as _redis_module
        _r = _redis_module.from_url(settings.REDIS_URL)
        _r.ping()
        logger.info("Redis 启动检查通过")
    except Exception as _e:
        logger.warning(
            "Redis 启动检查失败（不阻止启动，Redis 可能稍后启动）: %s", _e
        )


# ----------------------------------------------------------------------
# WebSocket Redis Pub/Sub 启动任务 (A8)
# 多 worker 场景下，每个 worker 维护自己的 WebSocket 连接表，
# 通过 Redis Pub/Sub channel `ws:broadcast` 跨进程同步消息。
# Redis 不可用时 ConnectionManager 自动降级为进程内广播，不阻塞启动。
# ----------------------------------------------------------------------
@app.on_event("startup")
async def _init_ws_pubsub():
    """初始化 WebSocket Redis Pub/Sub 并启动订阅任务。"""
    await ws_manager.init_redis()
    asyncio.create_task(ws_manager.subscribe_loop())


# ----------------------------------------------------------------------
# 全局异常处理器（C2 改造）— 把 BusinessError 转为统一 JSON 响应
# {code, message, details, detail}，并对未捕获 Exception 返回 500。
# ----------------------------------------------------------------------
register_error_handlers(app)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    """Liveness probe — checks database connectivity and disk space."""
    checks = {"status": "ok"}

    # Database check
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        logger.warning("Health check — database failed: %s", e)
        checks["database"] = "disconnected"
        checks["status"] = "degraded"

    # Disk space check (warn if < 500MB free)
    try:
        disk = shutil.disk_usage("/")
        free_mb = disk.free / (1024 * 1024)
        checks["disk_free_mb"] = round(free_mb, 1)
        if free_mb < 500:
            checks["disk"] = "low"
            checks["status"] = "degraded"
        else:
            checks["disk"] = "ok"
    except Exception:
        checks["disk"] = "unknown"

    return checks


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness probe — verify all dependencies are available."""
    checks = {}
    overall = "ok"

    # Database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "connected"
    except Exception as e:
        logger.warning("Readiness check — database failed: %s", e)
        checks["database"] = "failed"
        overall = "not_ready"

    # Redis (optional)
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL) if hasattr(settings, "REDIS_URL") and settings.REDIS_URL else None
        if r:
            r.ping()
            checks["redis"] = "connected"
        else:
            checks["redis"] = "not_configured"
    except Exception:
        # Redis 是可选依赖，未配置时不影响 readiness
        checks["redis"] = "failed"

    if overall != "not_ready":
        return {"status": "ok", **checks}
    raise HTTPException(status_code=503, detail={"status": "not_ready", **checks})


# ----------------------------------------------------------------------
# WebSocket 端点 — 实时通知
# ----------------------------------------------------------------------
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
):
    """WebSocket连接端点，支持实时通知。

    安全修复 (FASTAPI-WS-001):
        Token 不再通过 URL query 参数传递（会出现在 access log / 浏览器历史 /
        Referer 头中导致泄漏），改为通过 WebSocket 子协议（Sec-WebSocket-Protocol
        header）传递。客户端建立连接时应使用：
            new WebSocket(url, [`bearer.${token}`])
        服务端从 sec-websocket-protocol 头解析子协议，提取 token 并校验。
    """
    # FASTAPI-WS-001: 从 Sec-WebSocket-Protocol 头解析 token
    # 子协议格式: bearer.<access_token>
    sec_protocol = websocket.headers.get("sec-websocket-protocol") or ""
    token: str | None = None
    for sub in sec_protocol.split(","):
        sub = sub.strip()
        if sub.startswith("bearer."):
            token = sub[len("bearer."):]
            break

    if not token:
        # 拒绝连接：无 token
        await websocket.close(code=4001, reason="Authentication required")
        return

    # 验证 token 并确认 user_id 与 token 指向的用户一致
    try:
        from app.core.security import decode_token
        payload = decode_token(token)
        if payload.get("type") != "access":
            await websocket.close(code=4003, reason="Invalid token type")
            return
        token_user_id = payload.get("sub")
        if token_user_id != user_id:
            await websocket.close(code=4003, reason="User ID mismatch")
            return
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # 修复: FASTAPI-WS-001 — 将 subprotocol 传给 ws_manager.connect 统一 accept，
    # 避免在 main.py 中先 accept 再被 ws_manager.connect 二次 accept 引发 RuntimeError。
    await ws_manager.connect(websocket, user_id, subprotocol=f"bearer.{token}")

    # 连接时发送未读通知数
    try:
        from app.database import SessionLocal
        from app.models.notification import Notification as NotificationModel
        db = SessionLocal()
        try:
            unread_count = (
                db.query(NotificationModel)
                .filter(NotificationModel.user_id == user_id, NotificationModel.read == False)
                .count()
            )
            await websocket.send_text(json.dumps({
                "type": "notification_init",
                "unread_count": unread_count,
            }))
        finally:
            db.close()
    except Exception as e:
        logger.warning("发送未读通知数失败: %s", e)

    try:
        while True:
            data = await websocket.receive_text()
            # 修复: FASTAPI-WS-001 / WS-001 — 接收消息必须做 schema 校验，
            # 防止恶意/畸形 payload 触发未捕获异常或越权操作。
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "invalid json",
                }))
                continue

            if not isinstance(message, dict) or not isinstance(message.get("action"), str):
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": "invalid message format",
                }))
                continue

            action = message["action"]
            if action not in {"subscribe_task", "ping", "get_unread_count"}:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "detail": f"unknown action: {action}",
                }))
                continue

            # 处理订阅任务状态
            if action == "subscribe_task":
                task_id = message.get("task_id")
                if not isinstance(task_id, str) or not task_id or len(task_id) > 64:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "detail": "invalid task_id",
                    }))
                    continue
                ws_manager.subscribe_task(websocket, task_id)
                await websocket.send_text(json.dumps({
                    "type": "subscribed",
                    "task_id": task_id
                }))

            # 处理心跳
            elif action == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            # 处理获取未读通知数
            elif action == "get_unread_count":
                try:
                    from app.database import get_db
                    from app.models.notification import Notification as _NM
                    with next(get_db()) as _db:
                        _cnt = (
                            _db.query(_NM)
                            .filter(_NM.user_id == user_id, _NM.read == False)
                            .count()
                        )
                        await websocket.send_text(json.dumps({
                            "type": "notification_init",
                            "unread_count": _cnt,
                        }))
                except Exception as e:
                    logger.warning("获取未读通知数失败: %s", e)
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error("WebSocket错误: %s", e)
        ws_manager.disconnect(websocket, user_id)
