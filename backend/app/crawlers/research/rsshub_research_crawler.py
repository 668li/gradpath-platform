"""RSSHub 聚合订阅爬虫 — 批量订阅研招/教育部公告路由，走 PENDING 审核队列。

数据源：自建 RSSHub 实例（docker，http://127.0.0.1:1200）。
  - 一次性订阅 19 个实测可用的研究生院/研招网路由 + 教育部政策解读，
    替代「逐校爬研招官网公告」（原 30-60 分钟/源 → 5 分钟/源）
  - 上游源站全部为高校官网/教育部公开公告（edu.cn / gov.cn）

合规（对齐项目红线 + Mimosa 约束）：
- **本机白名单放行**：RSSHub 是项目自建可信实例。路由必须来自内置常量
  DEFAULT_ROUTES 集合（硬编码、不接受任何外部输入），URL 严格形如
  http://127.0.0.1:1200/{route}?limit=N；其余 URL 一律走父类严格校验
  （拒绝 localhost/私有地址）→ 不存在 SSRF 注入面
- **robots**：RSSHub 本机实例无 robots.txt，白名单路由跳过 robots 检查
  （上游源站合规由 RSSHub 路由配置承担，项目自身不直接请求源站）；
  非白名单 URL 的 robots 检查保持父类 fail-safe 逻辑
- 禁止路由：yz.chsi.com.cn 相关（/chsi/*）绝不订阅（项目红线）
- 全部入库走 store_research_items → PENDING 人工审核，无旁路

运行：py -3.13 -m app.crawlers.run --source rsshub_research
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[3]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

import feedparser
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.crawlers.research.rss_news_crawler import _extract_text, _parse_time_struct
from app.crawlers.research.transformer import ResearchTransformer
from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun
from app.services.research_ingestion import store_research_items

logger = logging.getLogger(__name__)

# 本机 RSSHub 实例（项目自建，docker run -p 1200:1200 diygod/rsshub）
RSSHUB_BASE = "http://127.0.0.1:1200"
RSSHUB_HOST = "127.0.0.1"

# 实测可用路由（2026-08-16 逐路由 HTTP 200 验证；503=上游暂不可达，保留待恢复）。
# 全部为高校研究生院/研招办公开公告，来源域名 edu.cn。
DEFAULT_ROUTES: list[str] = [
    "cau/yjs",                    # 中国农业大学研究生院
    "dhu/yjs/news",               # 东华大学研究生院新闻
    "ecnu/yjs",                   # 华东师范大学研究生院
    "hust/yjs",                   # 华中科技大学研究生院
    "nankai/yzb",                 # 南开大学研究生招生
    "nenu/yjsy",                  # 东北师范大学研究生院
    "nudt/yjszs",                 # 国防科技大学研究生招生
    "scnu/yjs",                   # 华南师范大学研究生院
    "scut/yjs",                   # 华南理工大学研究生院
    "sdu/cs/yjsgz",               # 山东大学计算机学院研究生工作
    "sdust/yjsy/zhaosheng",       # 山东科技大学研究生招生
    "seu/yjs",                    # 东南大学研究生院
    "snnu/yjs",                   # 陕西师范大学研究生院
    "sustech/yjs",                # 南方科技大学研究生院
    "swjtu/gsee/yjs",             # 西南交大地球科学与环境工程研究生
    "tju/yzb",                    # 天津大学研究生招生
    "tongji/yjs",                 # 同济大学研究生院
    "upc/yjs",                    # 中国石油大学研究生院
    "gov/moe/policy_anal",        # 教育部政策解读（gov.cn）
    # 资讯流（杠杆 #5，2026-08-16）：知乎日报/想法热榜，只存标题+摘要+链接，正文跳原文
    "zhihu/daily",                # 知乎日报（30 条/次，实测 200）
    "zhihu/pin/hotlist",          # 知乎想法热榜（15 条/次，实测 200）
]

# 资讯流路由 → 资讯分类（研招公告路由保持原分类；未知资讯流路由回落原逻辑）
_ROUTE_CATEGORY: dict[str, str] = {
    "zhihu/daily": "资讯·知乎日报",
    "zhihu/pin/hotlist": "资讯·知乎热榜",
}

# 每个路由拉取条数（RSSHub ?limit= 参数）
LIMIT = 15


@register_crawler
class RSSHubCrawler(BaseCrawler):
    """RSSHub 聚合订阅爬虫（研招公告 + 教育部政策解读）。"""

    name = "rsshub_research"
    category = "research"
    description = "RSSHub 聚合订阅（19 个研招路由 + 教育部，PENDING 审核队列）"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.routes = [r for r in self.config.get("routes", DEFAULT_ROUTES) if r]
        # 硬编码路由集合：任何不在该集合内的路径一律拒绝（防注入）
        self._allowed_routes: frozenset[str] = frozenset(DEFAULT_ROUTES)
        self._rate_limit = self.config.get("rate_limit", 1.0)
        self.keywords = [k.strip().lower() for k in self.config.get("keywords", []) if k.strip()]

    # ===== 安全校验覆盖：白名单路由放行，其余走父类严格校验 =====

    def _validate_outbound_url(self, url: str) -> tuple[bool, str]:
        """仅放行本机 RSSHub 白名单路由；其余 URL 一律父类严格校验（拒绝内网）。"""
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host == RSSHUB_HOST:
            path = (parsed.path or "").lstrip("/")
            if path in self._allowed_routes:
                return True, ""
            return False, f"RSSHub 路径不在白名单: {path}"
        return super()._validate_outbound_url(url)

    def _check_robots_allowed(self, url: str) -> bool:
        """本机 RSSHub 白名单路由跳过 robots（自建实例无 robots.txt）；其余父类逻辑。"""
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host == RSSHUB_HOST:
            return True
        return super()._check_robots_allowed(url)

    # ===== fetch：逐个路由拉取 RSS =====

    def fetch(self) -> list[dict]:
        all_entries: list[dict] = []
        for route in self.routes:
            if route not in self._allowed_routes:
                logger.warning(f"[{self.name}] 路由不在白名单，跳过: {route}")
                self.stats["errors"] += 1
                continue
            url = f"{RSSHUB_BASE}/{route}?limit={LIMIT}"
            try:
                resp = self._request(url)
                parsed = feedparser.parse(resp.content)
                if parsed.bozo and parsed.bozo_exception:
                    logger.warning(f"[{self.name}] {route} 解析警告: {parsed.bozo_exception}")
                feed_title = parsed.feed.get("title", "") if parsed.feed else route
                for entry in parsed.entries:
                    all_entries.append({
                        "_route": route,
                        "_feed_title": feed_title,
                        "entry": entry,
                    })
                logger.info(f"[{self.name}] {route} 获取 {len(parsed.entries)} 条")
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"[{self.name}] {route} 抓取失败（如实记录，跳过）: {e}")
        return all_entries

    # ===== parse：复用 rss_news 的字段抽取 =====

    def parse(self, raw_items: list[dict]) -> list[dict]:
        parsed: list[dict] = []
        for raw in raw_items:
            entry = raw["entry"]
            feed_title = raw.get("_feed_title", "")
            # 对齐 transform_rss 语义：RSSHub summary 常为 HTML 片段，需剥标签 + 截断
            # （否则 summary >500 字符导致 KaoyanNewsResponse schema 校验失败）
            title = ResearchTransformer._clean_text(
                ResearchTransformer._strip_html(_extract_text(entry, "title") or "无标题")
            )
            summary = ResearchTransformer._clean_text(
                ResearchTransformer._strip_html(_extract_text(entry, "summary", "description"))
            )[:500]
            content = ResearchTransformer._clean_text(
                ResearchTransformer._strip_html(_extract_text(entry, "content", "summary", "description"))
            )
            source_url = entry.get("link", "") or entry.get("id", "")
            if not source_url:
                logger.debug(f"[{self.name}] 跳过无 source_url 的条目: {title[:40]}")
                continue
            published_at = _parse_time_struct(
                getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            )
            item = {
                "title": title,
                "summary": summary,
                "content": content,
                "source_url": source_url,
                "published_at": published_at.isoformat() if published_at else None,
                "tags": [],
                "category": self._category_for(raw["_route"], feed_title),
                "source_platform": "rsshub",
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }
            parsed.append(item)
        return parsed

    def _category_for(self, route: str, feed_title: str) -> str:
        """资讯流路由按映射分类；研招公告路由保持「研招公告·{源}」原格式。"""
        for prefix, cat in _ROUTE_CATEGORY.items():
            if route.startswith(prefix):
                return cat[:50]
        return f"研招公告·{feed_title}"[:50]

    def _matches_keywords(self, item: dict) -> bool:
        """标题或摘要包含任一关键词时保留；无关键词时全部保留。"""
        if not self.keywords:
            return True
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        return any(kw in text for kw in self.keywords)

    # ===== store：CrawlerRun + PENDING 审核队列 =====

    def store(self, items: list[dict], db: Session = None) -> int:
        own_db = False
        if db is None:
            db = SessionLocal()
            own_db = True
        try:
            run_record = CrawlerRun(
                source_name=self.name,
                category=self.category,
                status="running",
            )
            db.add(run_record)
            db.commit()
            db.refresh(run_record)

            filtered_items = [item for item in items if self._matches_keywords(item)]
            result = store_research_items(
                db,
                crawler_name=self.name,
                item_type="kaoyan_news",
                items=filtered_items,
                source_platform="rsshub",
                run_id=str(run_record.id),
            )

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "routes": self.routes,
                "rsshub_base": RSSHUB_BASE,
                "platform": "rsshub",
            }
            db.commit()

            self.stats["stored"] = result["inserted"]
            self.stats["duplicates"] += result["duplicated"]
            logger.info(
                f"[{self.name}] 入库 {result['inserted']} 条新资讯，去重 {result['duplicated']} 条"
            )
            return result["inserted"]
        except Exception:
            db.rollback()
            raise
        finally:
            if own_db:
                db.close()


def main() -> None:
    crawler = RSSHubCrawler()
    raw = crawler.fetch()
    parsed = crawler.parse(raw)
    crawler.stats["fetched"] = len(parsed)
    stored = crawler.store(parsed)
    print(
        f"[{crawler.name}] 抓取 {len(raw)} 条原始 / 解析 {len(parsed)} 条 / "
        f"入库 {stored} 条 | 失败 {crawler.stats['errors']} 个路由（如实记录）"
    )


if __name__ == "__main__":
    main()
