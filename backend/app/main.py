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
# 路由导入放在 limiter 创建之后，避免循环导入
# ----------------------------------------------------------------------
from app.api.metrics import router as metrics_router
from app.api.search import router as search_router
from app.api.ai import router as ai_router
from app.api.assessment import router as assessment_router
from app.api.auth import router as auth_router
from app.api.career_plans import router as career_plans_router
from app.api.career_profile import router as career_profile_router
from app.api.chat import router as chat_router
from app.api.community import router as community_router
from app.api.admin.research import router as research_admin_router
from app.api.crawlers import router as crawlers_router
from app.api.dashboard import router as dashboard_router
from app.api.decision_analysis import router as decision_analysis_router
from app.api.decision_journal import router as decision_journal_router
from app.api.decisions import router as decisions_router
from app.api.employment import router as employment_router
from app.api.events import router as events_router
from app.api.export import router as export_router
from app.api.gamification import router as gamification_router
from app.api.grad_intel import router as grad_intel_router
from app.api.grad_visualization import router as grad_visualization_router
from app.api.career_intel import router as career_intel_router
from app.api.civil_service_intel import router as civil_service_intel_router
from app.api.experience_posts import router as experience_posts_router
from app.api.growth_patterns import router as growth_patterns_router
from app.api.interview import router as interview_router
from app.api.kaoyan_news import router as kaoyan_news_router
from app.api.knowledge import router as knowledge_router
from app.api.qa import router as qa_router
from app.api.life_design import router as life_design_router
from app.api.life_wheel import router as life_wheel_router
from app.api.mentors import router as mentors_router
from app.api.pipeline import router as pipeline_router
from app.api.plan_templates import router as plan_templates_router
from app.api.posts import router as posts_router
from app.api.proactive_insights import router as proactive_insights_router
from app.api.retrospectives import router as retrospectives_router
from app.api.skills import router as skills_router
from app.api.streaks import router as streaks_router
from app.api.study_plan import router as study_plan_router
from app.api.learning_resource import router as learning_resource_router
from app.api.skills_management import router as skills_management_router
from app.api.bookmarks import router as bookmarks_router
from app.api.comments import router as comments_router
from app.api.recommendations import router as recommendations_router
from app.api.notifications import router as notifications_router

app.include_router(auth_router)
app.include_router(decisions_router)
app.include_router(events_router)
app.include_router(skills_router)
app.include_router(retrospectives_router)
app.include_router(dashboard_router)
app.include_router(employment_router)
app.include_router(community_router)
app.include_router(interview_router)
app.include_router(pipeline_router)
app.include_router(posts_router)
app.include_router(ai_router)
app.include_router(gamification_router)
app.include_router(export_router)
# Phase 11 AI 职业管家
app.include_router(knowledge_router)
app.include_router(chat_router)
app.include_router(career_plans_router)
app.include_router(career_profile_router)
app.include_router(plan_templates_router)
app.include_router(assessment_router)
# 护城河功能
app.include_router(life_wheel_router)
app.include_router(streaks_router)
app.include_router(proactive_insights_router)
app.include_router(decision_journal_router)
# 护城河功能 - 深度价值
app.include_router(life_design_router)
app.include_router(decision_analysis_router)
app.include_router(mentors_router)
app.include_router(growth_patterns_router)
app.include_router(grad_intel_router)
app.include_router(grad_visualization_router)
app.include_router(career_intel_router)
app.include_router(civil_service_intel_router)
# 考研社区交流系统
app.include_router(experience_posts_router)
app.include_router(qa_router)
# 考研外部资讯
app.include_router(kaoyan_news_router)
# 学习规划与资源
app.include_router(study_plan_router)
app.include_router(learning_resource_router)
# Skill 管理（6 个项目专用 skill）
app.include_router(skills_management_router)
# 爬虫管理（管理员专用）
app.include_router(crawlers_router)
# 外部调研管理（管理员专用）
app.include_router(research_admin_router)
# 收藏
app.include_router(bookmarks_router)
# 评论系统
app.include_router(comments_router)
# AI 推荐
app.include_router(recommendations_router)
# 通知系统
app.include_router(notifications_router)
# Metrics endpoint
app.include_router(metrics_router)
# Monitor API
from app.api.monitor import router as monitor_router
app.include_router(monitor_router)
# 全文搜索
app.include_router(search_router)
# AI Agent (unified endpoint: DB + web search + LLM)
from app.api.ai_agent import router as ai_agent_router
app.include_router(ai_agent_router)

# AI 增强功能
from app.api.ai_enhanced import router as ai_enhanced_router
from app.api.analytics_api import router as analytics_router
from app.api.rag_admin_api import router as rag_admin_router
app.include_router(ai_enhanced_router)
app.include_router(analytics_router)
app.include_router(rag_admin_router)


# fastapi-mcp 暂时禁用（递归问题）
# try:
#     from fastapi_mcp import FastApiMCP
#
#     mcp_server = FastApiMCP(
#         app,
#         name="GradPath MCP",
#         description="GradPath 职业规划平台 — MCP 工具集，提供考研导师评价、院校情报、职业规划等功能",
#     )
#     # 挂载 MCP server 到 /mcp 路径
#     # 注意：此操作必须在所有路由注册之后执行
#     mcp_server.mount_http()
#     logger.info("MCP server 已挂载到 /mcp")
# except ImportError:
#     logger.warning("fastapi-mcp 未安装，跳过 MCP server 挂载")


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
