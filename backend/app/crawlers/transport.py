"""统一传输层 — 全部外发 HTTP 请求的唯一咽喉（数据地基①，spec 002 FR1）。

所有爬虫线的网络往返只允许经 ``fetch()`` 发生：per-host 礼貌限速、错误分级重试、
抓取证据（状态码+时刻+内容 sha256）在这里一次性做好，每条线白拿。

护栏分工：
- 红线域名（研招网 yz.chsi.com.cn）**分层处置**——"不碰"先于"入库拒收"：
  · 非白名单路径（网报/调剂/登录/专业目录查询等业务系统）在本层直接拒绝外发；
  · 白名单公开静态路径（``REDLINE_ALLOWED_PATHS``）条件放行，但强制
    per-domain 间隔 ≥ ``REDLINE_MIN_INTERVAL_S``、遇 WAF 即域级熔断。
  · research_ingestion 的入库拒收闸**仍对红线域全部拒收**（复用同一份名单，
    单一事实源在本模块）——外发放行 ≠ 入库放行，两道闸各司其职。
  · 依据：2026-09-30 用户拍板"内部辅助"——数据仅供本项目决策引擎使用，
    不转售、不做数据产品、不提供批量接口；自划线数据的真正源头是各高校
    自身发布，研招网为官方转载方之一。
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

# 研招网红线（2026-09-06 对抗审计 F2 定名；2026-09-12 起本层拒绝外发；
# 2026-09-30 用户拍板"内部辅助"后改为分层处置）。
# 只此一份名单：入库咽喉（research_ingestion）与外发闸（本模块）共用。
# 本常量一字不改——下游四处 import 依赖它（外发闸/入库咽喉/promote 纵深/审核兜底）。
REDLINE_FETCH_HOSTS = ("yz.chsi.com.cn",)

# 条件放行的公开静态路径前缀（红线域内）。当前仅自划线专题所在路径。
# 不含网报系统、调剂系统、学信网账号体系、专业目录查询（/zsml/ 需登录态遍历）。
REDLINE_ALLOWED_PATHS = ("/kyzx/",)

# 红线域条件放行时的 per-domain 限速下限（秒）。不因调用方配置更宽松而降低。
REDLINE_MIN_INTERVAL_S = 5.0


def is_redline_fetch_url(url: str) -> bool:
    """URL 主机是否落在红线域名（含子域）。外发闸与入库闸共用。"""
    hostname = (urlparse(url).hostname or "").lower()
    return any(hostname == h or hostname.endswith("." + h) for h in REDLINE_FETCH_HOSTS)


def classify_redline_url(url: str) -> str | None:
    """红线 URL 的外发处置分类。

    Returns:
        ``None``          —— 非红线域，正常放行
        ``"blocked"``     —— 红线域且路径不在白名单，硬拒外发
        ``"conditional"`` —— 红线域且路径在白名单，条件放行（限速加严 + 熔断生效）
    """
    if not is_redline_fetch_url(url):
        return None
    path = urlparse(url).path or "/"
    if any(path.startswith(p) for p in REDLINE_ALLOWED_PATHS):
        return "conditional"
    return "blocked"


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
    """同域请求间隔 ≥ min_interval；锁只保护字典读写，绝不跨 sleep 持锁。

    首次访问某域（桶为空）不等待——避免所有新域的第一请求被凭空延迟；
    该豁免仅对普通域成立，红线域走 :func:`_host_throttle_redline`。
    """
    while True:
        with _host_lock:
            now = time.monotonic()
            wait = min_interval - (now - _host_last_ts.get(host, 0.0))
            if wait <= 0:
                _host_last_ts[host] = now
                return
        time.sleep(wait)


def _host_throttle_redline(host: str, min_interval: float) -> None:
    """红线域限速（预约制）：任意两次实际放行间隔 ≥ min_interval，冷桶首击亦然。

    槽位语义 = 下一次允许放行的最早时刻：
    · 认领时 ``send_at = max(now, slot)``（冷桶视为 ``now + min_interval``），
      认领后槽位前移为 ``send_at + min_interval`` —— 并发调用各自拿到错开的
      放行时刻，不会在同一瞬间扎堆；
    · 长时间空闲后槽位早已过期：按 ``now`` 放行，不凭空追加延迟。

    与 :func:`_host_throttle` 的差别：普通域冷桶豁免（首请求不等），
    红线域不豁免——条件放行路径的首击同样受下限约束（2026-09-30 拍板口径）。
    """
    with _host_lock:
        now = time.monotonic()
        slot = _host_last_ts.get(host)
        if slot is None:
            send_at = now + min_interval
        else:
            send_at = max(now, slot)
        _host_last_ts[host] = send_at + min_interval
        wait = send_at - now
    if wait > 0:
        time.sleep(wait)


# ===== 域级熔断（WAF 表达"不欢迎"后停止对该域的全部请求） =====

# 命中即视为目标站明确拒绝：403 常规拒绝、412/488 常见于 WAF 挑战页。
# 换 UA / 换 IP 继续撞属"强行突破反爬技术措施"，不做。
_QUARANTINE_STATUSES = frozenset({403, 412, 488})
_QUARANTINE_TTL_S = 3600.0  # 隔离时长；到期后允许重探（WAF 策略可能已变）

_host_quarantine: dict[str, float] = {}


def _mark_quarantine(host: str) -> None:
    """把域记入隔离名单（到期时刻为值）。"""
    with _host_lock:
        _host_quarantine[host] = time.monotonic() + _QUARANTINE_TTL_S


def _quarantined_host(host: str) -> bool:
    """该域当前是否处于隔离期（过期自动清除）。"""
    with _host_lock:
        until = _host_quarantine.get(host)
        if until is None:
            return False
        if time.monotonic() >= until:
            _host_quarantine.pop(host, None)
            return False
        return True


def _reset_quarantine_for_tests() -> None:
    """清空域级隔离名单（测试隔离用，避免进程级状态跨用例污染）。"""
    with _host_lock:
        _host_quarantine.clear()
        _host_last_ts.clear()


# ===== 错误分级常量 =====

FOUR29_COOLDOWN_S = 20.0  # 429 停 20s 后放弃本轮
_RETRY_BACKOFF_BASE_S = 2.0  # 指数退避基数：2s/4s/8s


def _default_sender(method: str, url: str, headers: dict | None, timeout: float):
    """默认发送函数：httpx 直连（跟随重定向；UA 由调用方 headers 传或缺省）。"""
    import httpx

    send_headers = dict(headers or {})
    send_headers.setdefault(
        "User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"
    )
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
    host = (urlparse(url).hostname or "").lower()
    redline_verdict = classify_redline_url(url)

    if redline_verdict == "blocked":
        raise HttpFetchError(f"{tag}红线域名禁止外发: {url}", 0)
    if _quarantined_host(host):
        raise HttpFetchError(
            f"{tag}目标域已隔离（WAF 拒绝，{_QUARANTINE_TTL_S:.0f}s 内不再请求）: {url}", 403
        )

    # 红线域条件放行时限速加严：调用方配置更宽松也不下调。
    effective_rate = (
        max(rate_limit, REDLINE_MIN_INTERVAL_S) if redline_verdict == "conditional" else rate_limit
    )

    last_error: TransportError | None = None

    for attempt in range(max(1, max_retries)):
        if redline_verdict == "conditional":
            _host_throttle_redline(host, effective_rate)
        else:
            _host_throttle(host, effective_rate)
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
            if status in _QUARANTINE_STATUSES:
                _mark_quarantine(host)
                logger.warning(
                    f"{tag}HTTP {status} 视为 WAF 拒绝，域 {host} 隔离 {_QUARANTINE_TTL_S:.0f}s: {url}"
                )
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
