"""FastAPI 全局异常处理器 — 把 BusinessError 转为统一 JSON 响应。

统一错误响应格式：
    {
        "code": "NOT_FOUND",
        "message": "资源不存在",
        "details": {}
    }

为兼容历史调用方（前端 client.ts 解析 detail 字段），同时返回 detail 字段，
其值与 message 相同。
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import BusinessError

logger = logging.getLogger("gradpath.errors")


def register_error_handlers(app: FastAPI) -> None:
    """在 FastAPI app 上注册全局异常处理器。"""

    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        """业务异常统一处理：返回对应状态码与 code/message/details。"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                # 兼容字段：前端老代码读取 detail
                "detail": exc.message,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """兜底异常处理：记录日志但不向客户端泄露内部错误细节。

        注意：HTTPException / RequestValidationError / RateLimitExceeded /
        BusinessError 等已注册更具体的处理器，MRO 匹配会优先命中它们，
        不会被此兜底处理器捕获。
        """
        logger.exception("未处理的异常: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {},
                "detail": "服务器内部错误",
            },
        )
