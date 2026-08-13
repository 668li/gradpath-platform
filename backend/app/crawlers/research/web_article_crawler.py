"""网页文章调研爬虫 — 基于 Jina Reader 读取网页正文。"""
import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

# 当脚本被直接运行时，将 backend 目录加入 sys.path，确保 app 包可导入
_SCRIPT_PATH = Path(__file__).resolve()
_BACKEND_DIR = str(_SCRIPT_PATH.parents[3])
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from app.crawlers.base_crawler import BaseCrawler
from app.crawlers.registry import register_crawler
from app.database import SessionLocal
from app.models.crawler_run import CrawlerRun
from app.services.research_ingestion import store_research_items

logger = logging.getLogger(__name__)

JINA_READER_URL = "https://r.jina.ai/{url}"
OUTPUT_PATH = Path("/tmp/web_article_research.json")


@register_crawler
class WebArticleCrawler(BaseCrawler):
    """网页文章调研爬虫（Jina Reader）。"""

    name = "web_article_research"
    category = "research"
    description = "网页文章调研爬虫（Jina Reader）"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.urls: list[str] = self.config.get("urls", [])
        # 每个 URL 超时 15 秒、重试 2 次
        self.config.setdefault("max_retries", 2)
        self._rate_limit = self.config.get("rate_limit", 1.0)

    def fetch(self) -> list[dict]:
        """通过 Jina Reader 逐条读取 config["urls"] 中的 URL。"""
        if not self.urls:
            return []

        raw_items: list[dict] = []
        for url in self.urls:
            jina_url = JINA_READER_URL.format(url=url)
            text, error = self._fetch_with_retry(jina_url)
            if error is None:
                raw_items.append({
                    "url": url,
                    "text": text,
                    "status": "ok",
                })
                logger.info(f"[{self.name}] 成功读取: {url}")
            else:
                logger.warning(f"[{self.name}] 读取失败: {url} | {error}")
                raw_items.append({
                    "url": url,
                    "text": "",
                    "status": "error",
                    "error": error,
                })
            time.sleep(self._rate_limit)
        return raw_items

    def _fetch_with_retry(self, url: str) -> tuple[str, str | None]:
        """带超时与重试的 HTTP 请求，返回 (text, error_message)。"""
        max_retries = self.config.get("max_retries", 2)
        last_error = ""
        for attempt in range(max_retries + 1):
            try:
                resp = self.session.request("GET", url, timeout=15)
                resp.raise_for_status()
                return resp.text, None
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    wait = (attempt + 1) * 2
                    logger.warning(
                        f"[{self.name}] 请求失败({attempt + 1}/{max_retries + 1}), "
                        f"{wait}秒后重试: {e}"
                    )
                    time.sleep(wait)
        return "", last_error

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """从 Jina Reader 返回的文本中提取 title、content、source_url。"""
        parsed_items: list[dict] = []
        for raw in raw_items:
            url = raw.get("url", "")
            text = raw.get("text", "")
            status = raw.get("status", "")

            if status != "ok" or not text:
                parsed_items.append({
                    "title": url,
                    "content": "",
                    "source_url": url,
                    "source_platform": "web",
                    "status": "failed",
                })
                continue

            title = self._extract_title(text) or url
            content = self._extract_content(text, title)
            parsed_items.append({
                "title": title,
                "content": content,
                "source_url": url,
                "source_platform": "web",
                "status": "ok",
            })
        return parsed_items

    def _extract_title(self, text: str) -> str:
        """从 Jina Reader 文本中提取标题：优先第一行，否则第一个 # 标题。"""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return ""
        first_line = lines[0]
        # Jina Reader 常见格式：第一行就是标题
        if first_line and not first_line.startswith(("#", "*", "-", ">")):
            return first_line
        # 否则尝试匹配 Markdown # 标题
        for line in lines:
            match = re.match(r"^#+\s*(.+)$", line)
            if match:
                return match.group(1).strip()
        return first_line

    def _extract_content(self, text: str, title: str) -> str:
        """提取正文，去掉标题所在行。"""
        lines = text.splitlines()
        content_lines: list[str] = []
        title_found = False
        for line in lines:
            stripped = line.strip()
            if not title_found and stripped == title:
                title_found = True
                continue
            if not title_found and re.match(r"^#+\s*" + re.escape(title) + r"$", stripped):
                title_found = True
                continue
            content_lines.append(line)
        return "\n".join(content_lines).strip()

    def store(self, items: list[dict], db: Any = None) -> int:
        """将解析结果入库 t_external_research_item + t_review_queue_item。

        方案 C 主线 c（F9）：落盘爬虫改入库。
        - run() 被覆盖且无 db 参数，此处 db=None 时自建 session 兜底
        - 先创建一条 CrawlerRun 运行记录，再统一入库
        - OUTPUT_PATH 落盘保留为可选兼容：config.get("dump_json", False) 为 True 时才写
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
                item_type="dark_knowledge",
                items=items,
                source_platform="web",
                run_id=str(run_record.id),
            )

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "urls": self.urls,
                "platform": "web",
            }
            db.commit()

            self.stats["stored"] = result["inserted"]
            self.stats["duplicates"] += result["duplicated"]

            # 可选兼容：dump_json 为 True 时才写临时文件（CLI 老用法）
            if self.config.get("dump_json", False):
                OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
                with OUTPUT_PATH.open("w", encoding="utf-8") as f:
                    json.dump(items, f, ensure_ascii=False, indent=2)
                logger.info(f"[{self.name}] 已保存 {len(items)} 条到 {OUTPUT_PATH}")

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

    def run(self, db: Any = None) -> dict:
        """执行 fetch → parse → store，不依赖数据库会话。"""
        logger.info(f"[{self.name}] 开始爬取...")
        raw = self.fetch()
        self.stats["fetched"] = len(raw)
        logger.info(f"[{self.name}] 抓取到 {len(raw)} 条原始数据")

        parsed = self.parse(raw)
        logger.info(f"[{self.name}] 解析为 {len(parsed)} 条标准数据")

        stored = self.store(parsed)
        self.stats["stored"] = stored
        logger.info(f"[{self.name}] 入库 {stored} 条新数据")

        return {"status": "success", **self.stats}


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="网页文章调研爬虫（Jina Reader）")
    parser.add_argument(
        "--urls",
        type=str,
        required=True,
        help="待调研的 URL 列表，逗号分隔",
    )
    args = parser.parse_args()

    urls = [u.strip() for u in args.urls.split(",") if u.strip()]
    if not urls:
        parser.error("--urls 参数不能为空")

    crawler = WebArticleCrawler(config={"urls": urls})
    result = crawler.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
