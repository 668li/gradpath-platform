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

logger = logging.getLogger(__name__)


@register_crawler
class BilibiliResearchCrawler(BaseCrawler):
    """通过 B站搜索 API 抓取考研经验视频元数据，用于外部调研。"""

    name = "bilibili_research"
    category = "research"
    description = "B站考研经验视频调研爬虫"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.keyword = self.config.get("keyword", "408 计算机考研")
        self.pages = int(self.config.get("pages", 1))
        # 基类会按 _rate_limit 做固定睡眠，这里由本类自行控制 1-3 秒随机间隔
        self._rate_limit = 0
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
            ),
            "Referer": "https://search.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def fetch(self) -> list[dict]:
        """调用 B站搜索 API，分页抓取视频搜索结果。"""
        raw_items: list[dict] = []

        # 先访问首页获取必要的设备 Cookie（如 buvid3），降低被风控概率
        try:
            self._request("https://www.bilibili.com", method="GET")
            logger.info(f"[{self.name}] 首页预热完成")
        except Exception as e:
            logger.warning(f"[{self.name}] 首页预热失败: {e}")

        for page in range(1, self.pages + 1):
            url = (
                "https://api.bilibili.com/x/web-interface/search/type?"
                f"keyword={urllib.parse.quote(self.keyword)}"
                f"&search_type=video&page={page}"
            )
            try:
                resp = self._request(url, method="GET")
                data = resp.json()
                if data.get("code") != 0:
                    logger.error(
                        f"[{self.name}] 第{page}页 API 错误 "
                        f"code={data.get('code')}: {data.get('message')}"
                    )
                    self.stats["errors"] += 1
                    continue

                result = data.get("data", {}).get("result", [])
                if not result:
                    logger.info(f"[{self.name}] 第{page}页无结果，结束分页")
                    break

                raw_items.extend(result)
                logger.info(f"[{self.name}] 第{page}页获取 {len(result)} 条原始数据")
            except Exception as e:
                logger.error(f"[{self.name}] 第{page}页请求失败: {e}")
                self.stats["errors"] += 1

            if page < self.pages:
                time.sleep(random.uniform(1, 3))

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

    def store(self, items: list[dict], db) -> int:
        """将解析结果写入系统临时目录的 JSON 文件。"""
        tmp_dir = Path(tempfile.gettempdir())
        output_path = tmp_dir / f"bilibili_research_{self.keyword}.json"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        logger.info(f"[{self.name}] 已保存 {len(items)} 条到 {output_path}")
        return len(items)

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
    parser.add_argument("--keyword", required=True, help="搜索关键词")
    parser.add_argument("--pages", type=int, default=1, help="抓取页数")
    args = parser.parse_args()

    _setup_logging()
    crawler = BilibiliResearchCrawler(
        config={"keyword": args.keyword, "pages": args.pages}
    )

    raw = crawler.fetch()
    items = crawler.parse(raw)
    stored = crawler.store(items, db=None)

    print(f"抓取完成：原始 {len(raw)} 条，解析 {len(items)} 条，保存 {stored} 条")


if __name__ == "__main__":
    main()
