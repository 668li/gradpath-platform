"""统一传输层 — 全部外发 HTTP 请求的唯一咽喉（数据地基①，spec 002 FR1）。

所有爬虫线的网络往返只允许经 ``fetch()`` 发生：per-host 礼貌限速、错误分级重试、
抓取证据（状态码+时刻+内容 sha256）在这里一次性做好，每条线白拿。

护栏分工：
- 红线域名（研招网 yz.chsi.com.cn）在本层直接拒绝外发——"不碰"先于"入库拒收"；
  research_ingestion 的入库拒收闸复用同一份名单（单一事实源在本模块）。
- SSRF / robots 校验由调用方在入口执行（BaseCrawler 已有实现与测试），通过
  ``sender`` 注入发送函数——独立脚本（如 stats_gongbao）自带白名单校验。

错误分级（蓝图纪律）：
- 4xx 不重试——目标站明确拒绝，重试是无礼且浪费配额；
- 429 停 20 秒后放弃本轮（是否当天再试由调度层决定）；
- 5xx / 网络错误指数退避重试（2s/4s/8s）。

每次成功返回 :class:`FetchResult`，自带 ``evidence()``——入库三态闸
（fetched 必带证据）的数据源。兼容面：``.text/.status_code/.content/.encoding/
.headers/.json()/.raise_for_status()``，覆盖全部现存调用点。
"""

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# 研招网红线（2026-09-06 对抗审计 F2 定名；2026-09-12 起本层拒绝外发）。
# 只此一份名单：入库咽喉（research_ingestion）与外发闸（本模块）共用。
REDLINE_FETCH_HOSTS = ("yz.chsi.com.cn",)


def is_redline_fetch_url(url: str) -> bool:
    """URL 主机是否落在红线域名（含子域）。外发闸与入库闸共用。"""
    hostname = (urlparse(url).hostname or "").lower()
    return any(hostname == h or hostname.endswith("." + h) for h in REDLINE_FETCH_HOSTS)


class TransportError(requests.RequestException):
    """传输层失败基类。

    继承 requests.RequestException 保持既有异常兼容面（历史调用点与测试
    按 RequestException 捕获），语义上属于"统一传输层错误"。
    """


class HttpFetchError(TransportError):
    """HTTP 层失败（含状态码）。"""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class FetchResult:
    """一次成功外发请求的结果 + 抓取证据。"""

    url: str
    status_code: int
    text: str = ""
    content: bytes = b""
    headers: dict = field(default_factory=dict)
    encoding: str | None = None
    fetched_at: str = ""
    sha256: str = ""
    elapsed_s: float = 0.0

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HttpFetchError(f"HTTP {self.status_code}: {self.url}", self.status_code)

    def evidence(self) -> dict:
        """入库三态闸要求的抓取证据（http_status / fetched_at / sha256 三齐全）。"""
        return {
            "http_status": self.status_code,
            "fetched_at": self.fetched_at,
            "sha256": self.sha256,
            "url": self.url,
        }


# ===== per-host 共享限速桶（进程级；同域间隔 ≥ min_interval，跨域互不等待） =====

_host_lock = threading.Lock()
_host_last_ts: dict[str, float] = {}


def _host_throttle(host: str, min_interval: float) -> None:
    """同域请求间隔 ≥ min_interval；锁只保护字典读写，绝不跨 sleep 持锁。"""
    while True:
        with _host_lock:
            now = time.monotonic()
            wait = min_interval - (now - _host_last_ts.get(host, 0.0))
            if wait <= 0:
                _host_last_ts[host] = now
                return
        time.sleep(wait)


# ===== 错误分级常量 =====

FOUR29_COOLDOWN_S = 20.0  # 429 停 20s 后放弃本轮
_RETRY_BACKOFF_BASE_S = 2.0  # 指数退避基数：2s/4s/8s


def _default_sender(method: str, url: str, headers: dict | None, timeout: float):
    """默认发送函数：httpx 直连（跟随重定向；UA 由调用方 headers 传或缺省）。"""
    import httpx

    send_headers = dict(headers or {})
    send_headers.setdefault("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0")
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        return client.request(method, url, headers=send_headers)


def _read_response(resp) -> tuple[int, str, bytes, dict, str | None]:
    """从 httpx/requests 响应对象提取统一字段（兼容两种后端）。"""
    status = int(resp.status_code)
    content = resp.content or b""
    try:
        text = resp.text
    except Exception:
        text = content.decode("utf-8", errors="replace")
    headers = dict(getattr(resp, "headers", {}) or {})
    encoding = getattr(resp, "encoding", None)
    return status, text, content, headers, encoding


def fetch(
    url: str,
    *,
    method: str = "GET",
    headers: dict | None = None,
    timeout: float = 30.0,
    rate_limit: float = 1.0,
    max_retries: int = 3,
    crawler_name: str = "",
    sender=None,
) -> FetchResult:
    """发一次外发请求：红线闸 → per-host 限速 → 分级重试 → 证据。

    Args:
        sender: 可注入发送函数 ``(method, url, headers, timeout) -> response``；
            BaseCrawler 传自己的会话池（并发安全 + 测试打桩），缺省 httpx 直连。
    Returns:
        FetchResult（仅 2xx/3xx 终态会返回；失败按分级抛 TransportError）。
    """
    tag = f"[{crawler_name}] " if crawler_name else ""
    if is_redline_fetch_url(url):
        raise HttpFetchError(f"{tag}红线域名禁止外发: {url}", 0)

    host = (urlparse(url).hostname or "").lower()
    last_error: TransportError | None = None

    for attempt in range(max(1, max_retries)):
        _host_throttle(host, rate_limit)
        try:
            started = time.monotonic()
            resp = (sender or _default_sender)(method, url, headers, timeout)
            status, text, content, resp_headers, encoding = _read_response(resp)
            elapsed = time.monotonic() - started
        except TransportError:
            raise
        except Exception as e:  # 网络层错误（超时/连接/DNS）→ 可重试
            last_error = TransportError(f"{tag}网络错误: {e}")
            logger.warning(f"{tag}请求失败({attempt + 1}/{max_retries}): {e} | {url}")
            if attempt < max_retries - 1:
                time.sleep(_RETRY_BACKOFF_BASE_S * (2**attempt))
            continue

        if status == 429:
            logger.warning(f"{tag}429 限流，停 {FOUR29_COOLDOWN_S:.0f}s 后放弃本轮: {url}")
            time.sleep(FOUR29_COOLDOWN_S)
            raise HttpFetchError(f"{tag}429 限流: {url}", 429)
        if 400 <= status < 500:
            raise HttpFetchError(f"{tag}HTTP {status}: {url}", status)  # 4xx 不重试
        if status >= 500:
            last_error = HttpFetchError(f"{tag}HTTP {status}: {url}", status)
            logger.warning(f"{tag}服务端错误({attempt + 1}/{max_retries}) {status}: {url}")
            if attempt < max_retries - 1:
                time.sleep(_RETRY_BACKOFF_BASE_S * (2**attempt))
            continue

        return FetchResult(
            url=url,
            status_code=status,
            text=text,
            content=content,
            headers=resp_headers,
            encoding=encoding,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            sha256=hashlib.sha256(content).hexdigest(),
            elapsed_s=round(elapsed, 3),
        )

    raise last_error or TransportError(f"{tag}请求失败: {url}")
