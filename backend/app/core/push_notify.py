"""Server酱微信推送（运维告警统一出口）。

监控栈（monitoring/*.sh）用 curl 直推 Server酱；应用侧此前没有等价能力。
本模块补齐：慢查询严重告警、新用户反馈到达等场景的统一发送函数。

- fire-and-forget：调用方在请求热路径上时用 notify_async（后台线程），
  绝不阻塞业务；同步场景（脚本）用 send_serverchan。
- SSRF 防护：目标 URL 仅允许 https + Server酱官方域（sctapi.ftqq.com /
  sc.ftqq.com），非白名单域名一律拒绝发送。
- SERVERCHAN_WEBHOOK_URL 为空（本地开发/测试）时直接跳过。
"""

from __future__ import annotations

import logging
import threading
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Server酱官方 API 域白名单（SSRF 边界：协议+域名双重校验）
_ALLOWED_HOSTS = {"sctapi.ftqq.com", "sc.ftqq.com"}

# 并发闸：通知线程最多同时 3 个（httpx 10s 超时 → 最坏 30s 内饱和丢弃，
# 防反馈风暴下线程无界增长/Server酱被轰炸）；饱和时丢弃并记日志（通知可丢，业务不可阻）
_PUSH_SEMAPHORE = threading.Semaphore(3)


def _validated_url() -> str | None:
    url = (settings.SERVERCHAN_WEBHOOK_URL or "").strip()
    if not url:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS:
        logger.warning(
            "SERVERCHAN_WEBHOOK_URL 域名不在白名单（仅允许 %s），拒绝推送",
            sorted(_ALLOWED_HOSTS),
        )
        return None
    return url


def send_serverchan(title: str, desp: str = "") -> bool:
    """同步发送一条 Server酱消息。返回是否成功；未配置/域名不合法返回 False。"""
    url = _validated_url()
    if url is None:
        return False
    if not _PUSH_SEMAPHORE.acquire(blocking=False):
        logger.warning("Server酱推送通道饱和，丢弃: %s", title)
        return False
    try:
        resp = httpx.post(url, json={"title": title[:32], "desp": desp[:1800]},
                          timeout=10, follow_redirects=False)
        return resp.status_code == 200
    except Exception as e:  # noqa: BLE001 — 推送失败永不影响业务
        logger.warning("Server酱推送失败: %s", e)
        return False
    finally:
        _PUSH_SEMAPHORE.release()


def notify_async(title: str, desp: str = "") -> None:
    """后台线程发送（请求热路径用）。线程失败只留日志。"""

    def _run() -> None:
        send_serverchan(title, desp)

    threading.Thread(target=_run, daemon=True, name="serverchan-notify").start()
