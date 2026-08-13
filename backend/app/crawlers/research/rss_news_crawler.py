"""RSS 考研资讯爬虫 — 聚合多个公开 RSS 源，按关键词过滤并落地为 JSON。"""
import sys
from pathlib import Path

# 当以脚本形式从项目根目录运行时，把 backend 加入 sys.path
if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[3]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

import argparse
import json
import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun
from app.services.research_ingestion import store_research_items

logger = logging.getLogger(__name__)

# 默认订阅源：优先选择与考研、研究生教育相关的公开 RSS。
# 教育部、研招网等官方站点未提供原生 RSS，因此选用新浪教育考研频道、
# Reddit 研究生社区等可用源作为替代。
DEFAULT_FEEDS: list[str] = [
    "http://rss.sina.com.cn/edu/kaoyan.xml",  # 新浪教育-考研
    "https://www.reddit.com/r/GradSchool/.rss",  # Reddit 研究生社区
    "https://news.ycombinator.com/rss",  # Hacker News（作为通用技术/教育资讯补充）
]

# 默认不过滤关键词，确保默认运行能拿到足够条目
DEFAULT_KEYWORDS: list[str] = []

OUTPUT_PATH = Path("/tmp/rss_news_research.json")


def _parse_time_struct(ts: Any) -> datetime | None:
    """将 feedparser 的 UTC 时间元组转为 aware datetime。"""
    if ts is None:
        return None
    try:
        # feedparser 返回的 parsed time 为 UTC
        return datetime(*ts[:6], tzinfo=timezone.utc)
    except Exception:
        return None


def _extract_text(entry: Any, *attrs: str) -> str:
    """依次尝试从 entry 中抽取文本字段。"""
    for attr in attrs:
        value = getattr(entry, attr, None)
        if value:
            if isinstance(value, list) and value:
                # content 常见结构为 [{"value": "...", "type": "..."}]
                first = value[0]
                if isinstance(first, dict):
                    value = first.get("value", "")
                else:
                    value = str(first)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return ""


@register_crawler
class RssNewsCrawler(BaseCrawler):
    """RSS 考研资讯爬虫。"""

    name = "rss_news_research"
    category = "research"
    description = "RSS 考研资讯爬虫"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.feeds = self.config.get("feeds", DEFAULT_FEEDS)
        self.keywords = [k.strip().lower() for k in self.config.get("keywords", DEFAULT_KEYWORDS) if k.strip()]
        self.output_path = Path(self.config.get("output_path", OUTPUT_PATH))

    def fetch(self) -> list[dict]:
        """读取每个 feed，返回 entries 列表，每个 entry 携带来源 feed_url。"""
        all_entries: list[dict] = []
        for feed_url in self.feeds:
            if not feed_url:
                continue
            try:
                logger.info(f"[{self.name}] 抓取 RSS: {feed_url}")
                resp = self._request(feed_url)
                parsed = feedparser.parse(resp.content)
                if parsed.bozo and parsed.bozo_exception:
                    logger.warning(f"[{self.name}] {feed_url} 解析警告: {parsed.bozo_exception}")
                feed_title = parsed.feed.get("title", "") if parsed.feed else ""
                for entry in parsed.entries:
                    all_entries.append({
                        "_feed_url": feed_url,
                        "_feed_title": feed_title,
                        "entry": entry,
                    })
                logger.info(f"[{self.name}] {feed_url} 获取 {len(parsed.entries)} 条")
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"[{self.name}] 抓取 {feed_url} 失败: {e}")
        return all_entries

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将 feedparser entry 解析为标准资讯结构。"""
        parsed: list[dict] = []
        for raw in raw_items:
            entry = raw["entry"]
            feed_title = raw.get("_feed_title", "")

            title = _extract_text(entry, "title") or "无标题"
            summary = _extract_text(entry, "summary", "description")
            content = _extract_text(entry, "content", "summary", "description")
            source_url = entry.get("link", "")
            if not source_url:
                # 部分源使用 id 作为永久链接
                source_url = entry.get("id", "")
            if not source_url:
                logger.debug(f"[{self.name}] 跳过无 source_url 的条目: {title[:40]}")
                continue

            published_at = _parse_time_struct(
                getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
            )

            tags = []
            for tag in getattr(entry, "tags", []) or []:
                term = tag.get("term") if isinstance(tag, dict) else getattr(tag, "term", None)
                if term:
                    tags.append(term)

            item = {
                "title": title,
                "summary": summary,
                "content": content,
                "source_url": source_url,
                "published_at": published_at.isoformat() if published_at else None,
                "tags": tags,
                "category": feed_title or "research",
                "source_platform": "rss",
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }
            parsed.append(item)
        return parsed

    def _matches_keywords(self, item: dict) -> bool:
        """标题或摘要包含任一关键词时保留；无关键词时全部保留。"""
        if not self.keywords:
            return True
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        return any(kw in text for kw in self.keywords)

    def store(self, items: list[dict], db: Session = None) -> int:
        """入库 t_external_research_item + t_review_queue_item。

        方案 C 主线 c（F9）：落盘爬虫改入库。
        - 保留 _matches_keywords 关键词过滤
        - 去重改为依赖 DB 唯一索引（uk_external_research_item_source_url），
          不再读取/合并旧 JSON 文件
        - 先创建一条 CrawlerRun 运行记录，再统一入库
        - output_path 落盘保留为可选兼容：config.get("dump_json", False) 为 True 时才写
        """
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
                source_platform="rss",
                run_id=str(run_record.id),
            )

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "feeds": self.feeds,
                "keywords": self.keywords,
                "platform": "rss",
            }
            db.commit()

            self.stats["stored"] = result["inserted"]
            self.stats["duplicates"] += result["duplicated"]

            # 可选兼容：dump_json 为 True 时才写临时文件（CLI 老用法）
            if self.config.get("dump_json", False):
                self.output_path.parent.mkdir(parents=True, exist_ok=True)
                with self.output_path.open("w", encoding="utf-8") as f:
                    json.dump(filtered_items, f, ensure_ascii=False, indent=2)
                logger.info(f"[{self.name}] 已保存 {len(filtered_items)} 条到 {self.output_path}")

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


def _comma_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def main():
    parser = argparse.ArgumentParser(description="RSS 考研资讯爬虫 CLI")
    parser.add_argument(
        "--feeds",
        type=str,
        help="逗号分隔的 RSS 订阅源 URL 列表，覆盖默认值",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        help="逗号分隔的关键词列表，标题或摘要命中任一关键词才保留",
    )
    parser.add_argument(
        "--dump-json",
        action="store_true",
        help="额外将结果落盘到 JSON 文件（默认关闭，默认走数据库入库）",
    )
    args = parser.parse_args()

    config: dict[str, Any] = {}
    feeds = _comma_list(args.feeds)
    if feeds:
        config["feeds"] = feeds
    keywords = _comma_list(args.keywords)
    if keywords:
        config["keywords"] = keywords
    if args.dump_json:
        config["dump_json"] = True

    crawler = RssNewsCrawler(config=config)
    raw = crawler.fetch()
    parsed = crawler.parse(raw)
    stored = crawler.store(parsed, db=None)
    print(f"抓取 {len(raw)} 条，解析 {len(parsed)} 条，入库 {stored} 条")
    if args.dump_json:
        print(f"额外落盘文件: {crawler.output_path}")


if __name__ == "__main__":
    main()
