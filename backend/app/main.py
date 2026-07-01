import logging
import time
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import BusinessError
from app.core.logging import request_id_var, setup_logging
from app.database import Base, engine, get_db

# 配置结构化日志（尽早执行，确保后续组件日志统一格式 + request_id 追踪）
setup_logging(settings.LOG_LEVEL)

logger = logging.getLogger("gradpath")

app = FastAPI(title="GradPath API", version="0.1.0")

# ----------------------------------------------------------------------
# 限流器（slowapi）
# 必须在路由模块导入之前创建：路由模块会执行 `from app.main import limiter`，
# 若 limiter 尚未定义将触发循环导入错误。
# ----------------------------------------------------------------------
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
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

# ----------------------------------------------------------------------
# 请求日志中间件 — 为每个请求注入 request_id 并记录方法/路径/状态/耗时
# 通过 @app.middleware 注册，位于 CORS 之外（最外层），可记录完整请求链路。
# ----------------------------------------------------------------------
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    rid = uuid4().hex[:8]
    request_id_var.set(rid)
    request.state.request_id = rid
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
    return response

# ----------------------------------------------------------------------
# 路由导入放在 limiter 创建之后，避免循环导入
# ----------------------------------------------------------------------
from app.api.ai import router as ai_router
from app.api.assessment import router as assessment_router
from app.api.auth import router as auth_router
from app.api.career_plans import router as career_plans_router
from app.api.career_profile import router as career_profile_router
from app.api.chat import router as chat_router
from app.api.community import router as community_router
from app.api.gamification import router as gamification_router
from app.api.dashboard import router as dashboard_router
from app.api.decisions import router as decisions_router
from app.api.employment import router as employment_router
from app.api.events import router as events_router
from app.api.export import router as export_router
from app.api.interview import router as interview_router
from app.api.knowledge import router as knowledge_router
from app.api.pipeline import router as pipeline_router
from app.api.plan_templates import router as plan_templates_router
from app.api.posts import router as posts_router
from app.api.retrospectives import router as retrospectives_router
from app.api.skills import router as skills_router

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
def health():
    """Liveness probe — 进程存活即返回 ok。"""
    return {"status": "ok"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    """Readiness probe — 检查数据库连通性。"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.warning("Readiness check failed: %s", e)
        raise HTTPException(status_code=503, detail="数据库不可用")
