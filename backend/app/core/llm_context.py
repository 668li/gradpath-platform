# backend/app/core/llm_context.py
"""请求级 LLM 用户上下文 — BYOK 全局生效的底座。

纯 ASGI 中间件在每个请求入口从 Authorization Bearer token 解出 user_id
（仅 JWT 解码，无 DB 查询），存入 ContextVar；
``AIOrchestrator`` 构造时若未显式传 Key，则按该 user_id 解析用户自带的
LLM 配置（BYOK），使所有 LLM 调用点（导师人设 / 家庭对话 / 决策分析 /
研招情报等）无需逐个改造即自动支持用户自带 Key。

- 未登录 / token 无效：ContextVar 为空 → 走服务器默认配置
- Celery / 爬虫等无请求上下文的调用：同样走服务器默认配置
- 用纯 ASGI 中间件而非 BaseHTTPMiddleware：后者跨 task 的 ContextVar
  传播不可靠，纯 ASGI 包装在同一请求 task 内 set/reset，语义确定。
"""

import logging
from contextvars import ContextVar
from uuid import UUID

from app.core.security import decode_token

logger = logging.getLogger(__name__)

# 当前请求的用户 id（仅用于 LLM 配置解析；None = 无请求上下文或未认证）
current_llm_user_id: ContextVar[UUID | None] = ContextVar("current_llm_user_id", default=None)


class LLMUserContextMiddleware:
    """把 Bearer token 中的 user_id 注入 ContextVar 的纯 ASGI 中间件。"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        ctx_token = None
        try:
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode("latin-1").strip()
            if auth.lower().startswith("bearer "):
                payload = decode_token(auth[7:].strip())
                sub = payload.get("sub")
                if sub:
                    ctx_token = current_llm_user_id.set(UUID(str(sub)))
        except Exception:
            # token 无效/过期等：保持默认（服务器 Key），不影响请求本身
            pass
        try:
            await self.app(scope, receive, send)
        finally:
            if ctx_token is not None:
                current_llm_user_id.reset(ctx_token)
