"""外发 URL 安全校验 + robots.txt 合规（Mimosa 强制约束，BaseCrawler 与 Crawl4AIClient 共用）。

从 BaseCrawler 提取的模块级函数：
- ``validate_outbound_url``: 仅允许 http/https；拒绝 localhost/环回/私有/链路本地/
  多播/保留/未指定地址；域名经 socket 解析逐一校验（解析失败 fail-safe 拒绝）
- ``fetch_robots_parser``: robots.txt 拉取与解析（4xx 视为无 robots 放行；
  5xx / 网络失败 / 超时 → 无法确认，fail-safe 拒绝）
- ``RobotsChecker``: 带每主机缓存的 robots 判定器（Crawl4AIClient 自用；
  BaseCrawler 保留自己的实例缓存与打桩方法，见 base_crawler.py）

任何外发请求（HTTP 或浏览器渲染）都必须先过 ``validate_outbound_url``。
"""

import ipaddress
import logging
import socket
import threading
import urllib.error
import urllib.request
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

# SSRF 护栏：免解析即拒的保留主机名（其余经 socket 解析逐 IP 判定）
BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})


def validate_outbound_url(url: str) -> tuple[bool, str]:
    """校验外发 URL 是否安全。

    - 仅允许 http/https；拒绝 localhost/环回/私有/链路本地/多播/保留/未指定地址
    - 域名先字面判定，再 socket 解析逐一校验每个解析结果
    - 解析失败 / 解析到受限地址 → fail-safe 拒绝（不发起请求）
    Returns: (ok, reason)
    """
    try:
        parsed = urlparse(url)
    except ValueError as e:
        return False, f"URL 解析失败: {e}"
    if parsed.scheme not in ("http", "https"):
        return False, f"仅允许 http/https，收到: {parsed.scheme or '空'}"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "URL 缺少主机名"
    if host in BLOCKED_HOSTNAMES:
        return False, f"拒绝保留主机名: {host}"

    try:
        ips = [ipaddress.ip_address(host)]
    except ValueError:
        ips = resolve_host(host)
        if not ips:
            return False, f"域名解析失败（fail-safe 拒绝）: {host}"

    for ip in ips:
        if is_restricted_ip(ip):
            return False, f"目标解析到受限地址 {ip}（{host}）"
    return True, ""


def resolve_host(host: str) -> list:
    """解析域名为 IP 列表；解析失败返回空列表（调用方 fail-safe）。"""
    try:
        infos = socket.getaddrinfo(host, None)
    except (socket.gaierror, OSError):
        return []
    ips: list = []
    for info in infos:
        addr = info[4][0]
        try:
            ips.append(ipaddress.ip_address(addr))
        except ValueError:
            continue
    return ips


def is_restricted_ip(ip) -> bool:
    """是否受限地址：环回/私有/链路本地/多播/保留/未指定。

    IPv4 映射的 IPv6（::ffff:127.0.0.1）先解映射再判定，防绕过。
    """
    if ip.version == 6 and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    return (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def fetch_robots_parser(robots_url: str, user_agent: str) -> RobotFileParser | None:
    """拉取并解析 robots.txt；失败返回 None（fail-safe）。

    4xx（404/401 等）视为该站点无 robots.txt → 无规则放行；
    5xx / 网络失败 / 超时 → 无法确认，fail-safe 拒绝。
    """
    req = urllib.request.Request(robots_url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            logger.warning(f"robots.txt 服务器错误 {e.code}（fail-safe 拒绝）: {robots_url}")
            return None
        body = ""  # 404/401 等 → 视为无 robots.txt，放行
    except Exception as e:
        logger.warning(f"robots.txt 获取失败（fail-safe 拒绝）: {robots_url} | {e}")
        return None
    rp = RobotFileParser()
    rp.parse(body.splitlines())
    return rp


class RobotsChecker:
    """robots.txt 合规检查器：每主机解析一次并缓存，线程安全，fail-safe。

    供 Crawl4AIClient 等浏览器渲染请求使用。BaseCrawler 不经过这里：
    它保留自己的实例缓存与可打桩的 _check_robots_allowed/_fetch_robots_parser
    （既有测试对这两个方法做 monkeypatch，见 test_base_crawler.py）。
    """

    def __init__(self, user_agent: str):
        self.user_agent = user_agent
        self._cache: dict[str, RobotFileParser] = {}
        self._lock = threading.Lock()

    def check_allowed(self, url: str) -> bool:
        """按 USER_AGENT 判定该 URL 是否允许抓取。

        只对 http/https 生效；robots 获取失败或明确禁止 → fail-safe 返回 False
        （调用方跳过该 URL 并如实记录）。robots.txt 每主机拉取一次并缓存。
        """
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if not host:
            return False

        cache_key = f"{parsed.scheme}://{host}"
        with self._lock:
            rp = self._cache.get(cache_key)
        if rp is None:
            rp = fetch_robots_parser(cache_key, self.user_agent)
            if rp is None:
                return False  # robots 取不到 → fail-safe 拒绝
            with self._lock:
                self._cache[cache_key] = rp
        allowed = rp.can_fetch(self.user_agent, url)
        if not allowed:
            logger.warning(f"robots.txt 禁止抓取: {url}")
        return allowed
