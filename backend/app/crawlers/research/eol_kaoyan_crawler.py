"""中国教育在线考研频道爬虫 — kaoyan.eol.cn 考研快讯列表。

合规（Phase B1，外部调研确认）：
- robots.txt 仅 Disallow /include/ /dbrh/ /dyj/，列表页与详情页允许抓取
- 只抓公开列表页第一页（最新约 40 条）+ 逐条详情正文，不翻页不放大请求
- 串行 + rate_limit 默认 1.2s，继承 BaseCrawler 护栏

数据流向：列表页解析 (title, url, date) → 详情页 TRS_Editor 正文 →
ResearchTransformer.transform_rss（清洗/分类/质量分）→ store_research_items
（simhash 去重 + quality 过滤 → PENDING 审核队列），成功后回写 data_freshness。
"""
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

# 当以脚本形式从项目根目录运行时，把 backend 加入 sys.path
if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[3]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

import html as html_lib

from sqlalchemy.orm import Session

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.crawlers.research.transformer import ResearchTransformer
from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun
from app.models.ingestion import DataFreshness
from app.services.research_ingestion import store_research_items

logger = logging.getLogger(__name__)

# 考研快讯列表页（robots 允许）；相对链接基准为该页目录
DEFAULT_LIST_URL = "https://kaoyan.eol.cn/nnews/"
SOURCE_CHANNEL = "eol_kaoyan"  # 对应 data_freshness SOURCES 键

# 列表页条目块：fline 标题 + sline 详情链接 + tline 日期
_LIST_ITEM_RE = re.compile(
    r'<div class="fline">\s*<a href="(?P<url>[^"]+\.shtml)">(?P<title>.*?)</a>.*?'
    r'<span class="time">(?P<date>[^<]*)</span>',
    re.S,
)
_DETAIL_BODY_RE = re.compile(r'<div class=["\']?TRS_Editor["\']?[^>]*>(?P<body>.*?)</div>', re.S)


def _extract_detail_body(detail_html: str) -> str:
    """提取详情页 TRS_Editor 容器内的正文文本。

    TRS 编辑器正文结构简单（p 标签为主，无深嵌套），
    非贪婪匹配到第一个闭合 div 即可；失败返回空串。
    """
    m = _DETAIL_BODY_RE.search(detail_html or "")
    if not m:
        return ""
    text = re.sub(r"<[^>]+>", " ", m.group("body"))
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_date(value: str) -> datetime | None:
    """解析列表页日期（2026-07-30）为 aware datetime。"""
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


@register_crawler
class EolKaoyanCrawler(BaseCrawler):
    """中国教育在线考研频道资讯爬虫。"""

    name = "eol_kaoyan"
    category = "research"
    description = "中国教育在线考研频道资讯爬虫（eol.cn 考研快讯）"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.list_url = self.config.get("list_url", DEFAULT_LIST_URL)
        self._rate_limit = self.config.get("rate_limit", 1.2)
        # 详情页正文抓取开关：默认开；关闭时仅入库标题+摘要（列表页信息）
        self.fetch_detail = bool(self.config.get("fetch_detail", True))

    # ===== fetch：列表页 → 逐条详情页 =====

    def fetch(self) -> list[dict]:
        """抓取列表页并解析条目，逐条抓取详情页正文。"""
        resp = self._request(self.list_url)
        resp.encoding = "utf-8"
        html = resp.text

        items: list[dict] = []
        for m in _LIST_ITEM_RE.finditer(html):
            title = re.sub(r"\s+", " ", html_lib.unescape(m.group("title"))).strip()
            url = urljoin(self.list_url, m.group("url"))
            date = _parse_date(m.group("date"))
            if not title or not url:
                continue
            detail_text = ""
            if self.fetch_detail:
                detail_text = self._fetch_detail_text(url)
            items.append({
                "title": title,
                "url": url,
                "published_at": date,
                "detail_text": detail_text,
            })
        logger.info(f"[{self.name}] 列表页解析出 {len(items)} 条，详情抓取完成")
        return items

    def _fetch_detail_text(self, url: str) -> str:
        """抓取单条详情页正文；失败降级为空串（条目仍以列表信息入库）。"""
        try:
            resp = self._request(url)
            resp.encoding = "utf-8"
            return _extract_detail_body(resp.text)
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"[{self.name}] 详情页抓取失败，降级标题入库: {url} | {e}")
            return ""

    # ===== parse：复用 transformer 清洗/分类/质量分 =====

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将列表条目 + 详情正文转换为标准 KaoyanNews payload。

        复用 ResearchTransformer.transform_rss：统一走清洗/广告过滤/
        分类规则/质量分（quality_score/quality_grade 注入 payload，
        入库时由 research_ingestion 的 quality 过滤消费）。
        """
        raw_payloads: list[dict] = []
        for raw in raw_items:
            title = raw.get("title", "")
            detail = raw.get("detail_text", "")
            published_at = raw.get("published_at")
            # 详情正文前 300 字作摘要；无详情时用标题兜底
            summary = detail[:300] or title
            content = detail or summary
            raw_payloads.append({
                "title": title,
                "summary": summary,
                "content": content,
                "source_url": raw.get("url", ""),
                "published_at": published_at.isoformat() if published_at else None,
                "crawled_at": datetime.now(timezone.utc).isoformat(),
                "category": "考研快讯",
                "tags": [],
                "source_platform": "eol",
            })
        return ResearchTransformer.transform_rss(raw_payloads)

    # ===== store：CrawlerRun + 入库 + 回写 data_freshness =====

    def store(self, items: list[dict], db: Session = None) -> int:
        """入库 t_external_research_item + t_review_queue_item，回写 data_freshness。"""
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

            result = store_research_items(
                db,
                crawler_name=self.name,
                item_type="kaoyan_news",
                items=items,
                source_platform="eol",
                run_id=str(run_record.id),
            )

            # 回写 data_freshness（source_channel=eol_kaoyan，契约列见 DataFreshness）
            fresh = (
                db.query(DataFreshness)
                .filter(DataFreshness.source_name == SOURCE_CHANNEL)
                .first()
            )
            now = datetime.now(timezone.utc)
            if fresh is None:
                fresh = DataFreshness(source_name=SOURCE_CHANNEL)
                db.add(fresh)
            fresh.last_successful_crawl = now
            fresh.records_count = (fresh.records_count or 0) + result["inserted"]
            fresh.status = "active"
            fresh.updated_at = now

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "list_url": self.list_url,
                "fetch_detail": self.fetch_detail,
                "platform": "eol",
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


def main():
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="中国教育在线考研频道爬虫 CLI")
    parser.add_argument("--no-detail", action="store_true", help="跳过详情页正文抓取，仅列表信息入库")
    args = parser.parse_args()

    crawler = EolKaoyanCrawler(config={"fetch_detail": not args.no_detail})
    result = crawler.run()
    print(result)


if __name__ == "__main__":
    main()
