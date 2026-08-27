"""B站考研经验视频调研爬虫。"""

import argparse
import json
import logging
import random
import re
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path

# 当以脚本直接运行时，确保 backend 目录在 sys.path 中以便 import app
if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(backend_dir))

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun
from app.services.research_ingestion import store_research_items

logger = logging.getLogger(__name__)

# Phase H 默认关键词集（信息差高频维度，config 可覆盖；每次运行逐词抓取）
DEFAULT_KEYWORDS = [
    "408 计算机考研",
    "考研数学经验",
    "考研英语经验",
    "考研择校",
    "考研复试经验",
    "考研调剂",
    "备考时间规划",
    "考研二战 心态",
]


@register_crawler
class BilibiliResearchCrawler(BaseCrawler):
    """通过 B站搜索 API 抓取考研经验视频元数据，用于外部调研。

    Phase H：支持多关键词（config.keywords 列表 / CLI 逗号分隔），
    逐词分页抓取；合规不变 —— 只存元数据+简介+外链，不搬视频全文。
    """

    name = "bilibili_research"
    category = "research"
    description = "B站考研经验视频调研爬虫"

    def __init__(self, config: dict = None):
        super().__init__(config)
        raw_keywords = self.config.get("keywords") or []
        if isinstance(raw_keywords, str):
            raw_keywords = raw_keywords.split(",")
        self.keywords = [k.strip() for k in raw_keywords if k and k.strip()] or DEFAULT_KEYWORDS
        # 兼容旧字段：keyword 取第一个关键词（CLI 单关键词用法、source_meta 展示）
        self.keyword = self.keywords[0]
        self.pages = int(self.config.get("pages", 1))
        # 基类会按 _rate_limit 做固定睡眠，这里由本类自行控制 1-3 秒随机间隔
        self._rate_limit = 0
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                ),
                "Referer": "https://search.bilibili.com/",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            }
        )

    def fetch(self) -> list[dict]:
        """调用 B站搜索 API，逐关键词分页抓取视频搜索结果。"""
        raw_items: list[dict] = []

        # 先访问首页获取必要的设备 Cookie（如 buvid3），降低被风控概率
        try:
            self._request("https://www.bilibili.com", method="GET")
            logger.info(f"[{self.name}] 首页预热完成")
        except Exception as e:
            logger.warning(f"[{self.name}] 首页预热失败: {e}")

        for keyword in self.keywords:
            for page in range(1, self.pages + 1):
                url = (
                    "https://api.bilibili.com/x/web-interface/search/type?"
                    f"keyword={urllib.parse.quote(keyword)}"
                    f"&search_type=video&page={page}"
                )
                try:
                    resp = self._request(url, method="GET")
                    data = resp.json()
                    if data.get("code") != 0:
                        logger.error(
                            f"[{self.name}] 关键词[{keyword}] 第{page}页 API 错误 "
                            f"code={data.get('code')}: {data.get('message')}"
                        )
                        self.stats["errors"] += 1
                        continue

                    result = data.get("data", {}).get("result", [])
                    if not result:
                        logger.info(f"[{self.name}] 关键词[{keyword}] 第{page}页无结果，结束分页")
                        break

                    raw_items.extend(result)
                    logger.info(
                        f"[{self.name}] 关键词[{keyword}] 第{page}页获取 {len(result)} 条原始数据"
                    )
                except Exception as e:
                    logger.error(f"[{self.name}] 关键词[{keyword}] 第{page}页请求失败: {e}")
                    self.stats["errors"] += 1

                if page < self.pages:
                    time.sleep(random.uniform(1, 3))
            # 换关键词间隔拉长，降低风控概率
            if keyword != self.keywords[-1]:
                time.sleep(random.uniform(2, 4))

        return raw_items

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """将 B站搜索结果解析为标准经验贴结构。"""
        parsed_items: list[dict] = []
        for raw in raw_items:
            title_html = raw.get("title") or ""
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            bvid = raw.get("bvid") or ""
            source_url = raw.get("arcurl") or f"https://www.bilibili.com/video/{bvid}"
            description = raw.get("description") or raw.get("desc") or ""
            summary = description[:200] if description and description != "-" else title[:200]
            content = description if description and description != "-" else title
            tags_str = raw.get("tag") or ""
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]

            parsed_items.append(
                {
                    "title": title,
                    "summary": summary,
                    "content": content,
                    "author": raw.get("author", ""),
                    "bvid": bvid,
                    "source_url": source_url,
                    "view_count": self._to_int(raw.get("play")),
                    "like_count": self._to_int(raw.get("like")),
                    "tags": tags,
                    "category": self.config.get("post_category", "考研经验"),
                    "source_platform": "bilibili",
                }
            )
        return parsed_items

    def store(self, items: list[dict], db=None) -> int:
        """将解析结果入库 t_external_research_item + t_review_queue_item。

        方案 C 主线 c（F9）：落盘爬虫改入库。
        - 自建 session 兜底：main() 直调传 db=None，BaseCrawler.run 会传 db
        - 先创建一条 CrawlerRun 运行记录，再统一入库
        - 原 tempfile 落盘保留为可选兼容：config.get("dump_json", False) 为 True 时才写
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

            result = store_research_items(
                db,
                crawler_name=self.name,
                item_type="experience_post",
                items=items,
                source_platform="bilibili",
                run_id=str(run_record.id),
            )

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "keywords": self.keywords,
                "pages": self.pages,
                "platform": "bilibili",
            }
            db.commit()

            self.stats["stored"] = result["inserted"]
            self.stats["duplicates"] += result["duplicated"]

            # 可选兼容：dump_json 为 True 时才写临时文件（CLI 老用法）
            if self.config.get("dump_json", False):
                tmp_dir = Path(tempfile.gettempdir())
                output_path = tmp_dir / f"bilibili_research_{self.keyword}.json"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                logger.info(f"[{self.name}] 已保存 {len(items)} 条到 {output_path}")

            logger.info(
                f"[{self.name}] 入库 {result['inserted']} 条新数据，去重 {result['duplicated']} 条"
            )
            return result["inserted"]
        except Exception:
            db.rollback()
            raise
        finally:
            if own_db:
                db.close()

    @staticmethod
    def _to_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="B站考研经验视频调研爬虫")
    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
        help="搜索关键词（可多次传，或用逗号分隔多个；缺省用默认关键词集）",
    )
    parser.add_argument("--pages", type=int, default=1, help="每个关键词抓取页数")
    args = parser.parse_args()

    _setup_logging()
    keywords: list[str] = []
    for group in args.keyword:
        keywords.extend(k.strip() for k in group.split(",") if k.strip())
    crawler = BilibiliResearchCrawler(
        config={"keywords": keywords or DEFAULT_KEYWORDS, "pages": args.pages}
    )

    raw = crawler.fetch()
    items = crawler.parse(raw)
    stored = crawler.store(items, db=None)

    print(
        f"抓取完成：关键词 {len(crawler.keywords)} 个，"
        f"原始 {len(raw)} 条，解析 {len(items)} 条，入库 {stored} 条"
    )


if __name__ == "__main__":
    main()
