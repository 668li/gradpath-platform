import logging
import os
import shutil
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.gzip import GZipMiddleware

from app.config import settings
from app.core.exceptions import BusinessError
from app.core.logging import correlation_id_var, request_id_var, setup_logging
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.websocket_manager import manager as ws_manager
from app.database import Base, engine, get_db

# 配置结构化日志（尽早执行，确保后续组件日志统一格式 + request_id 追踪）
setup_logging(settings.LOG_LEVEL)

logger = logging.getLogger("gradpath")

app = FastAPI(
    title="GradPath API",
    description="GradPath 职业规划平台 — 提供考研导师评价、院校情报、职业规划、爬虫管理等功能",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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
# ----------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/hour"],
    headers_enabled=True,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS — 允许前端跨域访问（源由配置统一管理）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
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
    # Record metrics
    try:
        from app.api.metrics import record_request
        record_request(request.method, request.url.path, response.status_code, duration_ms)
    except Exception:
        pass
    return response

# ----------------------------------------------------------------------
# 路由自动发现：扫描 app.api 下所有模块的 router 并注册
# 新增 API 端点只需创建带 router 的 .py 文件，无需修改 main.py
# ----------------------------------------------------------------------
from app.api import auto_discover_routers
auto_discover_routers(app)


# 创建数据库表（仅开发模式；生产环境使用 Alembic 迁移）
# 必须在路由导入之后：路由导入触发模型注册到 Base.metadata
if settings.ENVIRONMENT == "development":
    Base.metadata.create_all(bind=engine)


# ----------------------------------------------------------------------
# 全局异常处理器
# ----------------------------------------------------------------------
@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    """业务异常统一处理：返回对应状态码与 detail。

    NotFoundError / ForbiddenError 等子类同样由此处理器处理（MRO 匹配）。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """兜底异常处理：记录日志但不向客户端泄露内部错误细节。

    注意：HTTPException / RequestValidationError / RateLimitExceeded 等已注册
    更具体的处理器，MRO 匹配会优先命中它们，不会被此兜底处理器捕获。
    """
    logger.exception("未处理的异常: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "服务器内部错误"},
    )


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
        checks["redis"] = "failed"
        # Redis is optional, don't fail readiness if not configured
        if checks.get("redis") != "not_configured":
            checks["redis"] = "failed"

    if overall != "not_ready":
        return {"status": "ok", **checks}
    raise HTTPException(status_code=503, detail={"status": "not_ready", **checks})


# ----------------------------------------------------------------------
import json
from fastapi import Query as FastAPIQuery

# WebSocket 端点 — 实时通知
# ----------------------------------------------------------------------
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    token: str = FastAPIQuery(...),
):
    """WebSocket连接端点，支持实时通知。

    安全修复：必须通过 token 参数验证用户身份，
    防止任意用户伪装成其他用户接收通知。
    """
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

    await ws_manager.connect(websocket, user_id)

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
        logger.warning(f"发送未读通知数失败: {e}")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理订阅任务状态
            if message.get("action") == "subscribe_task":
                task_id = message.get("task_id")
                if task_id:
                    ws_manager.subscribe_task(websocket, task_id)
                    await websocket.send_text(json.dumps({
                        "type": "subscribed",
                        "task_id": task_id
                    }))
            
            # 处理心跳
            elif message.get("action") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            # 处理获取未读通知数
            elif message.get("action") == "get_unread_count":
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
                    logger.warning(f"获取未读通知数失败: {e}")
                
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        ws_manager.disconnect(websocket, user_id)
