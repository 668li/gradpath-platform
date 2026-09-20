"""Outbound HTTP endpoint validation for user-supplied integrations.

The public web application must not let user-controlled URLs turn the backend
into an internal-network HTTP client. Development environments may keep local
HTTP endpoints for local LLM testing; production requires HTTPS and resolves
the host before allowing the request.
"""

from __future__ import annotations

import socket
from ipaddress import ip_address
from urllib.parse import urlparse

from app.config import settings


def validate_llm_base_url(base_url: str) -> None:
    """Validate a user-supplied OpenAI-compatible LLM endpoint.

    Raises:
        ValueError: when the URL is malformed or unsafe for the current
            environment.
    """
    parsed = urlparse((base_url or "").strip())

    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Base URL 必须使用 http(s)")

    if not parsed.hostname:
        raise ValueError("Base URL 缺少主机名")

    if parsed.username or parsed.password:
        raise ValueError("Base URL 不允许包含用户名或密码")

    if parsed.fragment:
        raise ValueError("Base URL 不允许包含 fragment")

    if settings.ENVIRONMENT != "production":
        return

    if parsed.scheme != "https":
        raise ValueError("生产环境的 LLM Base URL 必须使用 HTTPS")

    hostname = parsed.hostname
    try:
        infos = socket.getaddrinfo(
            hostname,
            parsed.port or 443,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError("Base URL 主机名无法解析") from exc

    addresses = {ip_address(info[4][0]) for info in infos}
    if not addresses:
        raise ValueError("Base URL 主机名无法解析")

    for address in addresses:
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise ValueError("生产环境的 LLM Base URL 不允许指向内网地址")
