"""Crawl4AIClient — crawl4ai 浏览器渲染抓取客户端（同步封装）。

为现有同步爬虫体系（BaseCrawler 为同步实现）提供 JS 渲染 + 结构化 markdown
抓取能力，同时保持与 HTTP 请求完全一致的合规护栏：

1. **SSRF（Mimosa 强制约束）**：每个 URL 发请求前都经
   ``url_safety.validate_outbound_url`` 校验（仅 http/https，拒绝
   localhost/环回/私有/保留地址，DNS 解析失败 fail-safe 拒绝）。
2. **robots.txt**：经 ``RobotsChecker`` 判定（每主机缓存一次，5xx/网络失败
   fail-safe 拒绝）。
3. **限速**：任意两次渲染之间至少间隔 ``CRAWL4AI_RATE_LIMIT`` 秒（默认 1.0），
   跨批与批内都生效。
4. **页数上限**：单次批量渲染页数受 ``CRAWL4AI_MAX_PAGES`` 限制（默认 10）。

设计要点：
- **懒初始化**：``get_instance()`` 首次调用才 import crawl4ai。crawl4ai 未安装 /
  浏览器不可用 / ``CRAWL4AI_ENABLED=false`` 时抛出 ``Crawl4aiError``，
  调用方捕获后降级到 BaseCrawler 的 HTTP 抽取（生产 Docker 镜像不装浏览器，
  即走降级路径）。
- **同步接口**：``fetch_markdown(url)`` / ``fetch_many(urls)``。crawl4ai 是
  async 库，内部经 ``asyncio.run`` 起一次浏览器会话批量渲染后关闭——
  每次调用是独立事件循环，浏览器实例不能跨循环存活，故按批起停（一次
  fetch_many 只启动一次浏览器，摊销启动成本）。
- 与既有 ad-hoc 脚本 ``crawl4ai_scraper.py`` 的区别：不绕过 SSRF、不落盘
  real_data、不在 import 时执行；请使用本客户端。

环境变量：CRAWL4AI_ENABLED（默认 true）、CRAWL4AI_TIMEOUT（默认 60000ms）、
CRAWL4AI_HEADLESS（默认 true）、CRAWL4AI_RATE_LIMIT（默认 1.0）、
CRAWL4AI_MAX_PAGES（默认 10）。
"""

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass

from app.crawlers.url_safety import RobotsChecker, validate_outbound_url

logger = logging.getLogger(__name__)

# 与 BaseCrawler.USER_AGENT 保持一致：robots.txt 按同一 UA 判定
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"

CRAWL4AI_ENABLED = os.getenv("CRAWL4AI_ENABLED", "true").strip().lower() in ("1", "true", "yes")
CRAWL4AI_TIMEOUT = int(os.getenv("CRAWL4AI_TIMEOUT", "60000"))
CRAWL4AI_HEADLESS = os.getenv("CRAWL4AI_HEADLESS", "true").strip().lower() in ("1", "true", "yes")
CRAWL4AI_RATE_LIMIT = float(os.getenv("CRAWL4AI_RATE_LIMIT", "1.0"))
CRAWL4AI_MAX_PAGES = int(os.getenv("CRAWL4AI_MAX_PAGES", "10"))


class Crawl4aiError(RuntimeError):
    """crawl4ai 不可用或抓取失败；调用方捕获后降级到 HTTP。"""


@dataclass
class Crawl4aiResult:
    """单页浏览器渲染结果。success=False 时 markdown 为空、error_message 说明原因。"""

    url: str
    markdown: str = ""
    title: str = ""
    success: bool = False
    error_message: str = ""
    status_code: int | None = None


class Crawl4AIClient:
    """同步包装 crawl4ai AsyncWebCrawler 的客户端（进程内单例）。"""

    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "Crawl4AIClient":
        """懒初始化单例：首次调用才建实例（不触发 crawl4ai import）。"""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self):
        if not CRAWL4AI_ENABLED:
            raise Crawl4aiError("CRAWL4AI_ENABLED=false，浏览器渲染已关闭")
        if CRAWL4AI_RATE_LIMIT < 0:
            raise Crawl4aiError("CRAWL4AI_RATE_LIMIT 不能为负数")
        self.rate_limit = CRAWL4AI_RATE_LIMIT
        self.max_pages = CRAWL4AI_MAX_PAGES
        self._robots_checker = RobotsChecker(USER_AGENT)
        # 跨批全局节流：与 BaseCrawler._request 的 _throttle_lock 机制一致
        self._throttle_lock = threading.Lock()
        self._last_render_ts = 0.0

    # ===== 公开同步接口 =====

    def fetch_markdown(self, url: str, **kwargs) -> Crawl4aiResult:
        """渲染单页为 markdown。安全护栏与 HTTP 请求一致（SSRF+robots+限速）。"""
        return self.fetch_many([url], **kwargs)[0]

    def fetch_many(self, urls: list[str], **kwargs) -> list[Crawl4aiResult]:
        """批量渲染（一次浏览器会话）；返回与 urls 顺序一一对应的结果列表。

        每个 URL 先经 validate_outbound_url + robots 判定，被拒绝的 URL
        不进入浏览器，直接返回 success=False 的结果（fail-safe）。
        """
        if not urls:
            return []
        if len(urls) > self.max_pages:
            logger.warning(
                f"[crawl4ai] 触发页数护栏: {len(urls)} 页 > CRAWL4AI_MAX_PAGES={self.max_pages}，截断"
            )
            urls = urls[: self.max_pages]

        # 预校验每个 URL：SSRF + robots。被拒的不进浏览器，直接占位（fail-safe）。
        # results 始终与输入顺序对齐：占位 None 在渲染后回填。
        pending_indices: list[int] = []
        results: list[Crawl4aiResult | None] = []
        for idx, url in enumerate(urls):
            ok, reason = validate_outbound_url(url)
            if not ok:
                logger.warning(f"[crawl4ai] 拒绝外发请求: {url} | {reason}")
                results.append(
                    Crawl4aiResult(url=url, success=False, error_message=f"URL 校验失败: {reason}")
                )
                continue
            if not self._robots_checker.check_allowed(url):
                results.append(
                    Crawl4aiResult(url=url, success=False, error_message="robots.txt 不允许抓取")
                )
                continue
            pending_indices.append(idx)
            results.append(None)

        if not pending_indices:
            return results  # type: ignore[return-value]

        page_timeout = kwargs.get("page_timeout", CRAWL4AI_TIMEOUT)
        wait_until = kwargs.get("wait_until", "domcontentloaded")
        pending_urls = [urls[i] for i in pending_indices]
        try:
            rendered = self._render_many_async(pending_urls, page_timeout, wait_until)
        except Crawl4aiError as e:
            # 浏览器不可用：pending 中所有 URL 均降级（调用方走 HTTP）
            for idx in pending_indices:
                results[idx] = Crawl4aiResult(url=urls[idx], success=False, error_message=str(e))
        else:
            for idx, res in zip(pending_indices, rendered):
                results[idx] = res
        return results  # type: ignore[return-value]

    # ===== async 渲染核心（每次调用独立事件循环，浏览器按批起停） =====

    def _render_many_async(
        self, urls: list[str], page_timeout: int, wait_until: str
    ) -> list[Crawl4aiResult]:
        """在单个事件循环内启动一次浏览器会话渲染所有 URL；返回与 urls 对齐的结果。"""
        timeout_ms = max(int(page_timeout), 1000)

        async def _render_all() -> list[Crawl4aiResult]:
            try:
                from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
            except ImportError as e:  # pragma: no cover - 环境缺依赖
                raise Crawl4aiError(f"crawl4ai 未安装: {e}") from e

            browser_cfg = BrowserConfig(
                headless=CRAWL4AI_HEADLESS,
                user_agent=USER_AGENT,
                verbose=False,
                ignore_https_errors=True,
                light_mode=True,
            )
            run_cfg = CrawlerRunConfig(
                verbose=False,
                page_timeout=timeout_ms,
                wait_until=wait_until,
                cache_mode=CacheMode.BYPASS,  # 公告页需实时渲染，不读旧缓存
                check_robots_txt=False,  # robots 已由 RobotsChecker 在浏览器外判过
                max_retries=2,
            )

            results: list[Crawl4aiResult] = []
            try:
                async with AsyncWebCrawler(config=browser_cfg) as crawler:
                    for i, url in enumerate(urls):
                        if i > 0:
                            await asyncio.sleep(self.rate_limit)  # 批内限速
                        self._throttle_cross_batch()  # 跨批限速（阻塞式，可接受）
                        results.append(await self._render_one(crawler, url, run_cfg))
            except Crawl4aiError:
                raise
            except Exception as e:  # 浏览器启动失败等 → 整批降级
                logger.warning(f"[crawl4ai] 浏览器渲染会话失败: {e}")
                raise Crawl4aiError(f"浏览器渲染失败: {e}") from e
            return results

        try:
            return asyncio.run(_render_all())
        except Crawl4aiError:
            raise

    async def _render_one(self, crawler, url: str, run_cfg) -> Crawl4aiResult:
        """渲染单个 URL 并归一化为 Crawl4aiResult；单页异常不影响批次其余页。"""
        try:
            container = await crawler.arun(url=url, config=run_cfg)
        except Exception as e:
            logger.warning(f"[crawl4ai] 单页渲染异常: {url} | {e}")
            return Crawl4aiResult(url=url, success=False, error_message=f"渲染异常: {e}")
        return self._to_result(url, container)

    @staticmethod
    def _to_result(url: str, container) -> Crawl4aiResult:
        """把 crawl4ai 的 CrawlResultContainer / CrawlResult 归一化为 Crawl4aiResult。"""
        res = getattr(container, "results", container)
        if isinstance(res, list):
            res = res[0] if res else None
        if res is None:
            return Crawl4aiResult(url=url, success=False, error_message="crawl4ai 无返回结果")

        markdown = getattr(res, "markdown", None) or ""
        if not markdown:
            markdown = getattr(res, "extracted_content", None) or ""
        metadata = getattr(res, "metadata", None) or {}
        title = (metadata.get("title") or "") if isinstance(metadata, dict) else ""
        return Crawl4aiResult(
            url=url,
            markdown=str(markdown),
            title=str(title),
            success=bool(getattr(res, "success", False)),
            error_message=getattr(res, "error_message", None) or "",
            status_code=getattr(res, "status_code", None),
        )

    def _throttle_cross_batch(self) -> None:
        """跨批限速：保证即使并发调用方也不突破 rate_limit（同 BaseCrawler 机制）。"""
        with self._throttle_lock:
            now = time.monotonic()
            wait = self.rate_limit - (now - self._last_render_ts)
            if wait > 0:
                time.sleep(wait)
            self._last_render_ts = time.monotonic()


def fetch_markdown(url: str, **kwargs) -> Crawl4aiResult | None:
    """模块级便捷入口：客户端不可用时返回 None（调用方降级 HTTP）。

    与 Crawl4AIClient.fetch_markdown 的区别仅在"客户端不可用 → None"：
    渲染本身失败仍返回 success=False 的结果对象。
    """
    try:
        return Crawl4AIClient.get_instance().fetch_markdown(url, **kwargs)
    except Crawl4aiError as e:
        logger.warning(f"[crawl4ai] 不可用，降级 HTTP: {e}")
        return None
