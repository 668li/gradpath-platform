"""爬虫基类 — 所有数据源爬虫继承此类。

合规护栏（红线：不批量抓取研招网、仅人工确认入库）：
- 单爬虫固定串行执行（并发=1，禁止多线程放大请求）
- ``max_pages`` / ``max_items`` 页数与条数上限，防止一次任务抓取量失控
- ``rate_limit`` 请求间隔（默认 1s），配合 max_retries 已内置
- 所有入库必须经人工确认（PENDING 审核队列），基类不提供绕过手段
"""

import ipaddress
import logging
import math
import socket
import threading
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.database import SessionLocal

if TYPE_CHECKING:
    from app.crawlers.crawl4ai_client import Crawl4aiResult
    from app.models.crawler_run import CrawlerRun

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """抽象基类：封装HTTP请求/解析/去重/入库/日志/重试/限速。"""

    # 子类必须覆盖
    name: str = ""  # 爬虫名称（唯一标识）
    category: str = ""  # 分类: grad/civil/career/reports
    description: str = ""  # 描述

    # 外发请求标识：robots.txt 按此 UA 判定；子类可覆盖（如 B站爬虫换浏览器 UA）
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GradPathCrawler/1.0"
    # SSRF 护栏：免解析即拒的保留主机名（其余经 socket 解析逐 IP 判定）
    _BLOCKED_HOSTNAMES = frozenset({"localhost", "localhost.localdomain"})

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.USER_AGENT})
        self.stats = {"fetched": 0, "stored": 0, "errors": 0, "duplicates": 0}
        self._rate_limit = self.config.get("rate_limit", 1.0)  # 默认1秒间隔
        # robots.txt 解析缓存（按 host 缓存一次，单次运行内不重复拉取）。
        # 并发爬虫共享实例时用锁保护 get/set，避免多线程同时拉取同一 host。
        self._robots_cache: dict[str, RobotFileParser] = {}
        self._robots_lock = threading.Lock()
        # stats 并发累加锁：并发爬虫下多线程对 self.stats["errors"] 等做 += 会丢计数
        self._stats_lock = threading.Lock()
        # 合规护栏：单次任务抓取上限（0 表示不限制，研招网来源必须显式配置）
        self._max_pages = int(self.config.get("max_pages", 0))
        self._max_items = int(self.config.get("max_items", 0))
        # 并发窗口：默认 1（串行）。>1 由子类在 fetch() 里启用并发 worker。
        # 并发时每线程用独立 Session（requests.Session 非线程安全），
        # 且用信号量把"同刻执行中的 HTTP 请求数"限制在窗口内，限速仍生效。
        self._concurrency = int(self.config.get("concurrency", 1))
        self._request_sem = threading.Semaphore(self._concurrency)
        # 每线程独立 Session 池：thread-id -> requests.Session
        self._thread_sessions: dict = {}
        self._thread_sessions_lock = threading.Lock()
        # 节流锁：按 host 分桶限速——同域请求间隔仍 ≥ _rate_limit，跨域互不拖累
        # （修复原全局串行"一慢全慢"缺陷；锁本身仍全局，保护分桶字典线程安全）
        self._throttle_lock = threading.Lock()
        self._last_request_ts_by_host: dict[str, float] = {}
        # 单行记账：一次爬取全程恰一行 CrawlerRun，行由子类 store() 创建
        # （run_id 溯源链在爬虫手上）；started_at/duration 以整个 run() 计。
        self.run_record_id = ""
        self._run_started_at = ""
        self._run_start_monotonic = 0.0

    @abstractmethod
    def fetch(self) -> list[dict]:
        """抓取数据，返回原始数据列表。子类必须实现。"""
        ...

    @abstractmethod
    def parse(self, raw_items: list[dict]) -> list[dict]:
        """解析原始数据为标准结构。子类必须实现。"""
        ...

    @abstractmethod
    def store(self, items: list[dict], db: Session) -> int:
        """存储数据到数据库，返回新增条数。子类必须实现。"""
        ...

    def run(self, db: Session = None) -> dict:
        """执行完整爬取流程：fetch → parse → store。"""
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True
        # 单行记账起点：行创建在子类 store()，started_at/duration 覆盖整个 run()
        self._run_started_at = datetime.now(timezone.utc).isoformat()
        self._run_start_monotonic = time.monotonic()
        try:
            logger.info(f"[{self.name}] 开始爬取...")
            raw = self.fetch()
            # 合规护栏：页数上限（max_pages），防止单次任务抓取量失控
            if self._max_pages > 0 and len(raw) > self._max_pages:
                logger.warning(
                    f"[{self.name}] 触发页数护栏: 抓取 {len(raw)} 条 > max_pages={self._max_pages}，截断"
                )
                raw = raw[: self._max_pages]
            self.stats["fetched"] = len(raw)
            logger.info(f"[{self.name}] 抓取到 {len(raw)} 条原始数据")

            parsed = self.parse(raw)
            # 合规护栏：条数上限（max_items）
            if self._max_items > 0 and len(parsed) > self._max_items:
                logger.warning(
                    f"[{self.name}] 触发条数护栏: 解析 {len(parsed)} 条 > max_items={self._max_items}，截断"
                )
                parsed = parsed[: self._max_items]
            logger.info(f"[{self.name}] 解析为 {len(parsed)} 条标准数据")

            stored = self.store(parsed, db)
            self.stats["stored"] = stored
            logger.info(f"[{self.name}] 入库 {stored} 条新数据")

            result = {"status": "success", **self.stats}
            if self.run_record_id:
                result["run_id"] = self.run_record_id
            return result
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"[{self.name}] 爬取失败: {e}")
            result = {"status": "failed", "error": str(e), **self.stats}
            if self.run_record_id:
                # 行已建但入库中途失败：回传 run_id 让包装层更新该行，不另建
                result["run_id"] = self.run_record_id
            return result
        finally:
            if own_db:
                db.close()

    # ===== 单行记账：CrawlerRun 行由爬虫内部创建（包装层只更新，不另建） =====

    def _new_run_record(self) -> "CrawlerRun":
        """创建本次爬取的执行记录行（一次爬取全程恰一行）。

        行创建放爬虫内部（store()）以维持 run_id 溯源链；started_at 取
        run() 起点而非 store() 时刻，duration 才覆盖整个抓取过程。
        """
        from app.models.crawler_run import CrawlerRun

        return CrawlerRun(
            source_name=self.name,
            category=self.category,
            status="running",
            started_at=self._run_started_at or None,
        )

    def _finalize_run_record(self, run_record: "CrawlerRun", status: str = "success") -> None:
        """入库完成后回填 finished_at / duration_seconds / 状态。"""
        run_record.status = status
        run_record.finished_at = datetime.now(timezone.utc).isoformat()
        if self._run_start_monotonic > 0:
            elapsed = time.monotonic() - self._run_start_monotonic
            # Integer 列向上取整：任何正时长记账都 >0（秒级观测粒度）
            run_record.duration_seconds = max(1, math.ceil(elapsed))

    def _throttle(self, host: str) -> None:
        """per-host 节流：同域请求间隔 ≥ _rate_limit，跨域互不等待。线程安全。

        锁只保护分桶字典读写，绝不跨 sleep 持锁——否则一个 host 的等待会把
        其他 host 全部堵在锁上，per-host 分桶就退化回全局串行。
        """
        while True:
            with self._throttle_lock:
                now = time.monotonic()
                wait = self._rate_limit - (now - self._last_request_ts_by_host.get(host, 0.0))
                if wait <= 0:
                    self._last_request_ts_by_host[host] = now
                    return
            time.sleep(wait)

    def _bump_stats(self, key: str, n: int = 1) -> None:
        """线程安全地累加 stats 计数（并发爬虫下避免 += 丢计数）。"""
        with self._stats_lock:
            self.stats[key] = self.stats.get(key, 0) + n

    def _get_session(self) -> requests.Session:
        """返回当前线程的独立 Session。

        requests.Session 非线程安全：并发爬虫下每个线程必须用自己
        的 Session，避免多线程共享连接池产生竞态。串行模式(并发=1)
        只有一个线程，退化为共享 self.session，行为与历史一致。
        """
        if self._concurrency <= 1:
            return self.session
        tid = threading.get_ident()
        with self._thread_sessions_lock:
            s = self._thread_sessions.get(tid)
            if s is None:
                s = requests.Session()
                s.headers.update({"User-Agent": self.USER_AGENT})
                self._thread_sessions[tid] = s
            return s

    def _request(self, url: str, method: str = "GET", **kwargs) -> requests.Response:
        """带限速和重试的HTTP请求。

        外发安全护栏（Mimosa 约束）：发请求前校验 host（仅 http/https，
        拒绝 localhost/环回/私有/保留地址，DNS 解析失败 fail-safe 拒绝）；
        robots.txt 不允许则跳过该 URL 并如实记录。

        并发安全：窗口内并发 HTTP 请求数受 self._request_sem 限制，且
        每次网络往返之间至少间隔 _rate_limit（全局串行化，保证限速不失效）。
        """
        ok, reason = self._validate_outbound_url(url)
        if not ok:
            logger.warning(f"[{self.name}] 拒绝外发请求: {url} | {reason}")
            raise requests.RequestException(f"外发 URL 校验失败: {reason}")
        if not self._check_robots_allowed(url):
            raise requests.RequestException(f"robots.txt 不允许抓取: {url}")
        max_retries = self.config.get("max_retries", 3)
        for attempt in range(max_retries):
            try:
                # 并发窗口信号量：限制同刻在飞的 HTTP 请求数（并发=1 时不阻塞）
                with self._request_sem:
                    # per-host 节流：同域间隔 ≥ _rate_limit；跨域并行互不等待
                    self._throttle((urlparse(url).hostname or "").lower())
                    resp = self._get_session().request(method, url, timeout=30, **kwargs)
                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 2
                    logger.warning(
                        f"[{self.name}] 请求失败({attempt+1}/{max_retries}), {wait}秒后重试: {e}"
                    )
                    time.sleep(wait)
                else:
                    raise

    # ===== 可选浏览器渲染抓取（crawl4ai 集成；客户端不可用时降级 HTTP） =====

    def fetch_markdown(self, url: str, **kwargs) -> "Crawl4aiResult | None":
        """可选浏览器渲染抓取：返回结构化 markdown；客户端不可用时返回 None。

        与 _request 相同的安全护栏（SSRF + robots.txt + 限速，实现在
        crawl4ai_client.py，任何 URL 发请求前都经 url_safety.validate_outbound_url
        校验）。crawl4ai 未安装 / CRAWL4AI_ENABLED=false 时返回 None，调用方
        降级到 _request 的 HTTP 抽取；渲染本身失败返回 success=False 的结果对象。
        """
        try:
            from app.crawlers.crawl4ai_client import Crawl4AIClient, Crawl4aiError
        except ImportError:
            return None
        try:
            return Crawl4AIClient.get_instance().fetch_markdown(url, **kwargs)
        except Crawl4aiError as e:
            logger.warning(f"[{self.name}] crawl4ai 不可用，降级 HTTP: {e}")
            return None

    # ===== 外发请求安全校验（Mimosa 强制约束：仅 http/https，拒绝内网/保留地址） =====

    def _validate_outbound_url(self, url: str) -> tuple[bool, str]:
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
        if host in self._BLOCKED_HOSTNAMES:
            return False, f"拒绝保留主机名: {host}"

        try:
            ips = [ipaddress.ip_address(host)]
        except ValueError:
            ips = self._resolve_host(host)
            if not ips:
                return False, f"域名解析失败（fail-safe 拒绝）: {host}"

        for ip in ips:
            if self._is_restricted_ip(ip):
                return False, f"目标解析到受限地址 {ip}（{host}）"
        return True, ""

    @staticmethod
    def _resolve_host(host: str) -> list:
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

    @staticmethod
    def _is_restricted_ip(ip) -> bool:
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

    # ===== robots.txt 合规（不绕过验证码、不爬登录内容；不允许即跳过） =====

    def _check_robots_allowed(self, url: str) -> bool:
        """robots.txt 合规检查：按 USER_AGENT 判定该 URL 是否允许抓取。

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
        with self._robots_lock:
            rp = self._robots_cache.get(cache_key)
        if rp is None:
            rp = self._fetch_robots_parser(cache_key)
            if rp is None:
                return False  # robots 取不到 → fail-safe 拒绝
            with self._robots_lock:
                self._robots_cache[cache_key] = rp
        allowed = rp.can_fetch(self.USER_AGENT, url)
        if not allowed:
            logger.warning(f"[{self.name}] robots.txt 禁止抓取: {url}")
        return allowed

    def _fetch_robots_parser(self, robots_url: str) -> RobotFileParser | None:
        """拉取并解析 robots.txt；失败返回 None（fail-safe）。

        4xx（404/401 等）视为该站点无 robots.txt → 无规则放行；
        5xx / 网络失败 / 超时 → 无法确认，fail-safe 拒绝。
        """
        req = urllib.request.Request(robots_url, headers={"User-Agent": self.USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code >= 500:
                logger.warning(
                    f"[{self.name}] robots.txt 服务器错误 {e.code}（fail-safe 拒绝）: {robots_url}"
                )
                return None
            body = ""  # 404/401 等 → 视为无 robots.txt，放行
        except Exception as e:
            logger.warning(
                f"[{self.name}] robots.txt 获取失败（fail-safe 拒绝）: {robots_url} | {e}"
            )
            return None
        rp = RobotFileParser()
        rp.parse(body.splitlines())
        return rp

    def _dedup_key(self, item: dict) -> str:
        """生成去重键，子类可覆盖。默认用所有字段拼接。"""
        return "|".join(str(v) for v in sorted(item.values()))

    # ===== 批量UPSERT方法 =====

    def batch_upsert(
        self,
        db: Session,
        model_class,
        items: list[dict],
        unique_key: str | list[str],
        batch_size: int = 200,
    ) -> int:
        """批量UPSERT：如果记录存在则更新，不存在则插入。

        Args:
            db: 数据库会话
            model_class: SQLAlchemy模型类
            items: 要插入/更新的数据列表
            unique_key: 去重键字段名（单字段字符串或字段名列表）
            batch_size: 每批处理的记录数

        Returns:
            新增或更新的记录数
        """
        if not items:
            return 0

        # 统一unique_key为列表
        if isinstance(unique_key, str):
            unique_key = [unique_key]

        # 去重：按unique_key保留最后一条记录
        seen = set()
        deduped = []
        for item in reversed(items):  # 反转后遍历，保留最后出现的
            key = tuple(item.get(k) for k in unique_key)
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        deduped.reverse()  # 恢复原始顺序

        # 方言判定：pg_insert(ON CONFLICT) 仅 PostgreSQL 支持。
        # SQLite（本地 dev / pytest）降级为"查重→仅插入缺失"，不做 UPDATE；
        # 生产环境强制 PostgreSQL，行为与 ON CONFLICT 一致。
        if db.get_bind().dialect.name == "sqlite":
            return self._sqlite_upsert(db, model_class, deduped, unique_key)

        total_affected = 0

        for i in range(0, len(deduped), batch_size):
            batch = deduped[i : i + batch_size]

            try:
                # 构建UPSERT语句
                stmt = pg_insert(model_class).values(batch)

                # 构建更新字典（排除unique_key字段）
                update_cols = {k: stmt.excluded[k] for k in batch[0] if k not in unique_key}

                if update_cols:
                    stmt = stmt.on_conflict_do_update(
                        index_elements=unique_key,
                        set_=update_cols,
                    )
                else:
                    stmt = stmt.on_conflict_do_nothing()

                result = db.execute(stmt)
                total_affected += result.rowcount
                db.flush()

            except Exception as e:
                logger.warning(f"[{self.name}] 批量UPSERT失败(batch {i//batch_size + 1}): {e}")
                # 回退到逐条处理
                for item in batch:
                    try:
                        stmt = pg_insert(model_class).values(**item)
                        update_cols = {
                            k: getattr(stmt.excluded, k) for k in item if k not in unique_key
                        }
                        if update_cols:
                            stmt = stmt.on_conflict_do_update(
                                index_elements=unique_key,
                                set_=update_cols,
                            )
                        db.execute(stmt)
                        total_affected += 1
                    except Exception as e2:
                        logger.error(f"[{self.name}] 单条UPSERT失败: {e2}")
                        self.stats["errors"] += 1

        db.commit()
        return total_affected

    def _sqlite_upsert(self, db: Session, model_class, items: list[dict], unique_key: list) -> int:
        """SQLite 降级批量入库：按 unique_key 查重后仅插入缺失记录。

        仅用于本地开发 / 测试（生产强制 PostgreSQL，走 batch_upsert 的 ON CONFLICT 精确 upsert）。
        复用 get_existing_keys 批量查重；所有值经 ORM 绑定参数注入，不拼接 SQL 字符串。
        注意：SQLite 降级只对单列唯一键做幂等去重；多列唯一键按首列近似去重，
        生产环境不受影响。
        """
        if not items:
            return 0

        key_field = unique_key[0]
        valid_cols = set(model_class.__table__.columns.keys())
        if key_field not in valid_cols:
            logger.error(f"[{self.name}] SQLite降级: 唯一键列 {key_field} 不存在，跳过本次入库")
            return 0

        existing_keys = self.get_existing_keys(
            db, model_class, key_field, [i.get(key_field) for i in items]
        )
        new_items = [i for i in items if i.get(key_field) not in existing_keys]
        for item in new_items:
            db.add(model_class(**item))
        db.commit()
        return len(new_items)

    def batch_upsert_simple(
        self,
        db: Session,
        model_class,
        items: list[dict],
        unique_key: str | list[str],
        batch_size: int = 200,
    ) -> int:
        """简化版批量UPSERT：适用于没有created_at/updated_at字段的模型。

        与batch_upsert相同，但跳过timestamp字段的更新。
        """
        return self.batch_upsert(db, model_class, items, unique_key, batch_size)

    def get_existing_keys(
        self,
        db: Session,
        model_class,
        key_field: str,
        values: list,
    ) -> set:
        """批量查询已存在的去重键，用于快速判断是否需要插入。

        Returns:
            已存在的键集合
        """
        if not values:
            return set()

        # 分批查询（避免IN子句过大）
        existing = set()
        batch_size = 500
        for i in range(0, len(values), batch_size):
            batch = values[i : i + batch_size]
            col = getattr(model_class, key_field)
            rows = db.query(col).filter(col.in_(batch)).all()
            existing.update(row[0] for row in rows)

        return existing
