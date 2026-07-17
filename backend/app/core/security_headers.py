"""Security response headers middleware.

Injects standard security headers to prevent clickjacking, MIME sniffing,
and downgrade attacks.
"""
from __future__ import annotations

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("gradpath.security")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject security response headers.

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - Strict-Transport-Security (production HTTPS only)
    - Referrer-Policy: strict-origin-when-cross-origin
    - X-XSS-Protection: 0 (modern browsers use built-in)
    - Content-Security-Policy: default-src restrictions
    - Permissions-Policy: restrict browser features
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Referrer policy — send only origin on cross-origin
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Modern browsers have built-in XSS protection; disable the outdated header
        response.headers["X-XSS-Protection"] = "0"

        # Permissions-Policy — restrict camera, microphone, geolocation
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )

        # Content Security Policy
        # 优化：connect-src 从环境变量动态构建，避免硬编码端口（原 bug：硬编码 8000 但后端实际在 8001）
        # CSP_CONNECT_SRC 可配置多个源，用空格分隔，例如："http://localhost:8001 http://localhost:3000"
        csp_connect_src = os.getenv("CSP_CONNECT_SRC", "http://localhost:8001")
        csp_directives = [
            "default-src 'self'",
            "script-src 'self'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' https://fonts.gstatic.com",
            f"connect-src 'self' {csp_connect_src}",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # HSTS — only on HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # No-cache for auth endpoints to prevent token leakage
        if request.url.path.startswith("/api/auth"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response
