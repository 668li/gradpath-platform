"""安全的出站 HTTP 地址校验。

用于 BYOK 等用户可控的服务器出站请求，阻断常见 SSRF 目标：
本机、私网、链路本地、保留/组播地址，以及非 HTTP(S) scheme。
"""

from ipaddress import ip_address
import socket
from urllib.parse import urlparse


class OutboundURLValidationError(ValueError):
    """用户提供的出站 URL 不允许访问。"""


def _is_disallowed_ip(raw: str) -> bool:
    ip = ip_address(raw)
    # IPv4-mapped IPv6 需要按其映射的 IPv4 地址再次判断。
    target = ip.ipv4_mapped or ip
    return any(
        (
            target.is_private,
            target.is_loopback,
            target.is_link_local,
            target.is_reserved,
            target.is_multicast,
            target.is_unspecified,
        )
    )


def validate_public_http_endpoint(base_url: str) -> str:
    """校验用户可控的 HTTP(S) endpoint，并返回规范化 URL。

    注意：这是应用层 SSRF 第一层防线；生产网络层仍应限制应用进程
    对 RFC1918、link-local、云元数据等地址的出站访问。
    """
    value = (base_url or "").strip()
    parsed = urlparse(value)

    if parsed.scheme.lower() not in {"http", "https"}:
        raise OutboundURLValidationError("Base URL 只能使用 http 或 https")
    if not parsed.hostname:
        raise OutboundURLValidationError("Base URL 缺少主机名")
    if parsed.username or parsed.password:
        raise OutboundURLValidationError("Base URL 不允许携带用户名或密码")
    if parsed.fragment:
        raise OutboundURLValidationError("Base URL 不允许包含 fragment")

    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)

    try:
        infos = socket.getaddrinfo(
            host,
            port,
            type=socket.SOCK_STREAM,
        )
    except (socket.gaierror, OSError) as exc:
        raise OutboundURLValidationError("Base URL 主机无法解析") from exc

    addresses = {item[4][0] for item in infos if item and item[4]}
    if not addresses:
        raise OutboundURLValidationError("Base URL 没有可用地址")

    for address in addresses:
        try:
            if _is_disallowed_ip(address):
                raise OutboundURLValidationError(
                    "Base URL 不允许指向本机、内网、链路本地或其他受限地址"
                )
        except ValueError as exc:
            raise OutboundURLValidationError("Base URL 解析到无效 IP 地址") from exc

    return value.rstrip("/")
