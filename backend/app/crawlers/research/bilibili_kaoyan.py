"""B站考研视频爬虫 — 搜索考研相关视频并写入 knowledge_articles 表。"""
import argparse
import logging
import re
import sys
import time
import urllib.parse
from pathlib import Path

if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(backend_dir))

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.models.knowledge_article import KnowledgeArticle

logger = logging.getLogger(__name__)


@register_crawler
class BilibiliKaoyanCrawler(BaseCrawler):
    """通过B站搜索API抓取考研视频，写入 knowledge_articles。"""

    name = "bilibili_kaoyan"
    category = "research"
    description = "B站考研视频爬虫"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.keyword = self.config.get("keyword", "考研")
        self.pages = int(self.config.get("pages", 5))
        # 禁用基类限速，由 fetch 自行控制2秒间隔
        self._rate_limit = 0
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Referer": "https://search.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def fetch(self) -> list[dict]:
        raw_items: list[dict] = []
        for page in range(1, self.pages + 1):
            url = (
                "https://api.bilibili.com/x/web-interface/search/type?"
                f"search_type=video&keyword={urllib.parse.quote(self.keyword)}&page={page}"
            )
            try:
                resp = self._request(url)
                data = resp.json()
                if data.get("code") != 0:
                    logger.error(f"[{self.name}] 第{page}页 API错误 code={data.get('code')}: {data.get('message')}")
                    self.stats["errors"] += 1
                    continue
                result = data.get("data", {}).get("result", [])
                if not result:
                    logger.info(f"[{self.name}] 第{page}页无结果，结束分页")
                    break
                raw_items.extend(result)
                logger.info(f"[{self.name}] 第{page}页获取 {len(result)} 条")
            except Exception as e:
                logger.error(f"[{self.name}] 第{page}页请求失败: {e}")
                self.stats["errors"] += 1
            if page < self.pages:
                time.sleep(2)
        return raw_items

    def parse(self, raw_items: list[dict]) -> list[dict]:
        parsed = []
        for raw in raw_items:
            title_html = raw.get("title") or ""
            title = re.sub(r"<[^>]+>", "", title_html).strip()
            if not title:
                continue
            bvid = raw.get("bvid") or ""
            author = raw.get("author") or ""
            description = raw.get("description") or raw.get("desc") or ""
            play = self._to_int(raw.get("play"))
            created = self._to_int(raw.get("created"))
            tags_str = raw.get("tag") or ""
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]

            parsed.append({
                "title": title,
                "content": description if description and description != "-" else title,
                "tags": tags,
                "source": "bilibili",
                "metadata": {
                    "source_type": "video",
                    "bvid": bvid,
                    "author": author,
                    "play": play,
                    "created": created,
                    "source_url": f"https://www.bilibili.com/video/{bvid}" if bvid else "",
                },
                "category": "education_path",
                "is_published": True,
            })
        return parsed

    def store(self, items: list[dict], db) -> int:
        if not items:
            return 0
        # 按bvid去重：先查已存在的bvid
        bvids = [item["metadata"]["bvid"] for item in items if item["metadata"].get("bvid")]
        existing = self.get_existing_keys(db, KnowledgeArticle, "metadata", [])
        # 从metadata中提取已存在的bvid（JSONB无法直接IN查询，用ORM逐条查）
        existing_bvids = set()
        if bvids:
            from sqlalchemy import text
            # 用JSONB @> 操作符查询已存在的bvid
            for bvid in bvids:
                rows = db.execute(
                    text("SELECT 1 FROM knowledge_articles WHERE metadata->>'bvid' = :bvid LIMIT 1"),
                    {"bvid": bvid}
                ).fetchall()
                if rows:
                    existing_bvids.add(bvid)

        new_items = []
        dup_count = 0
        for item in items:
            bvid = item["metadata"].get("bvid", "")
            if bvid and bvid in existing_bvids:
                dup_count += 1
                continue
            new_items.append(item)
        self.stats["duplicates"] = dup_count

        if not new_items:
            return 0

        # 批量插入
        stored = 0
        batch_size = 200
        for i in range(0, len(new_items), batch_size):
            batch = new_items[i:i + batch_size]
            try:
                db.bulk_insert_mappings(KnowledgeArticle, batch)
                db.flush()
                stored += len(batch)
            except Exception as e:
                logger.error(f"[{self.name}] 批量插入失败: {e}")
                db.rollback()
        db.commit()
        return stored

    @staticmethod
    def _to_int(value) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="B站考研视频爬虫")
    parser.add_argument("--keyword", default="考研", help="搜索关键词")
    parser.add_argument("--pages", type=int, default=5, help="抓取页数(每页50条)")
    args = parser.parse_args()

    crawler = BilibiliKaoyanCrawler(
        config={"keyword": args.keyword, "pages": args.pages}
    )
    result = crawler.run()
    print(f"\n===== 爬取报告 =====")
    print(f"爬取条数: {result.get('fetched', 0)}")
    print(f"导入条数: {result.get('stored', 0)}")
    print(f"去重条数: {result.get('duplicates', 0)}")
    print(f"错误条数: {result.get('errors', 0)}")
    print(f"状态: {result.get('status', 'unknown')}")


if __name__ == "__main__":
    main()
