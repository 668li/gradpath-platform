"""百度贴吧考研避坑帖调研爬虫（Phase I）。

只抓公开数据：列表页（tieba.baidu.com/f?kw=…）按避坑关键词过滤标题，
再抓公开帖子首页正文；登录内容不爬、robots 不允许 → fail-safe 跳过并如实记录。
入库走 store_research_items → PENDING 审核队列，人工确认后才落业务表。
"""

import argparse
import html
import json
import logging
import random
import re
import sys
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

# 避坑/教训类关键词（信息差高频维度；config.keywords 可覆盖）
DEFAULT_KEYWORDS = ["避坑", "踩坑", "教训", "劝退", "避雷", "别报", "不要报", "不建议"]

# 反爬/登录拦截标记（命中即丢弃该条，如实记录，绝不绕过）
_ANTI_CRAWL_MARKERS = ["安全验证", "CAPTCHA", "登录后查看", "请您登录", "请先登录"]

# 贴吧列表页帖子链接：/p/12345，标题在 <a ... class="j_th_tit ">标题</a>
_THREAD_LINK_RE = re.compile(
    r'href="(/p/(\d+))"[^>]*class="[^"]*j_th_tit[^"]*"[^>]*>(.*?)</a>', re.S
)
# 回退：任意 /p/ 链接 + 邻近标题
_THREAD_LINK_FALLBACK_RE = re.compile(r'<a[^>]*href="(/p/\d+)"[^>]*>(.*?)</a>', re.S)
# 帖子页标题
_TITLE_RE = re.compile(r'<h1[^>]*class="[^"]*core_title_txt[^"]*"[^>]*>(.*?)</h1>', re.S)
# 楼层正文（d_post_content）
_FLOOR_RE = re.compile(r'<div[^>]*class="[^"]*d_post_content[^"]*"[^>]*>(.*?)</div>', re.S)


def _strip_tags(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>|</(?:p|div|li|blockquote|h\d)>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = html.unescape(fragment)
    lines = [ln.strip() for ln in fragment.splitlines()]
    return "\n".join(ln for ln in lines if ln).strip()


@register_crawler
class TiebaResearchCrawler(BaseCrawler):
    """百度贴吧考研避坑帖调研爬虫。"""

    name = "tieba_research"
    category = "research"
    description = "百度贴吧考研避坑帖调研爬虫"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.forum = str(self.config.get("forum", "考研"))
        raw_keywords = self.config.get("keywords") or []
        if isinstance(raw_keywords, str):
            raw_keywords = raw_keywords.split(",")
        self.keywords = [k.strip() for k in raw_keywords if k.strip()] or DEFAULT_KEYWORDS
        self.pages = int(self.config.get("pages", 1))
        # 基类按 _rate_limit 固定睡眠，这里自行控制 1-3 秒随机间隔（控频）
        self._rate_limit = 0

    # ------------------------------------------------------------------
    # fetch → parse → store（基类 run 编排；store 走 PENDING 审核队列）
    # ------------------------------------------------------------------

    def fetch(self) -> list[dict]:
        """抓公开列表页 → 按避坑关键词过滤标题 → 抓帖子首页正文。"""
        raw_items: list[dict] = []
        # 先解析列表页，收集 (title, url) 候选项
        candidates: list[tuple[str, str]] = []
        for page in range(1, self.pages + 1):
            list_url = (
                "https://tieba.baidu.com/f?kw="
                f"{urllib.parse.quote(self.forum)}&ie=utf-8&pn={(page - 1) * 50}"
            )
            try:
                resp = self._request(list_url, method="GET")
            except Exception as e:
                logger.warning(f"[{self.name}] 列表页抓取失败: {list_url} | {e}")
                self.stats["errors"] += 1
                continue
            candidates.extend(self._parse_list_page(resp.text))
            if page < self.pages:
                time.sleep(random.uniform(1, 3))

        seen: set[str] = set()
        fetched = 0
        for title, url in candidates:
            if url in seen:
                continue
            seen.add(url)
            try:
                resp = self._request(url, method="GET")
            except Exception as e:
                logger.warning(f"[{self.name}] 帖子抓取失败: {url} | {e}")
                raw_items.append({"url": url, "html": "", "status": "error", "error": str(e)})
                continue
            raw_items.append({"url": url, "html": resp.text, "title_hint": title, "status": "ok"})
            fetched += 1
            logger.info(f"[{self.name}] 成功抓取: {title[:30]} ({url})")
            if self._max_items > 0 and fetched >= self._max_items:
                logger.info(f"[{self.name}] 达到 max_items={self._max_items}，停止抓取")
                break
            time.sleep(random.uniform(1, 3))
        return raw_items

    def _parse_list_page(self, html_text: str) -> list[tuple[str, str]]:
        """解析列表页帖子链接 + 标题，按避坑关键词过滤。"""
        result: list[tuple[str, str]] = []
        matches = _THREAD_LINK_RE.findall(html_text)
        if not matches:
            # 回退：任意 /p/ 链接 + 邻近标题（无 pid 提取）
            matches = [
                (href, "", title) for href, title in _THREAD_LINK_FALLBACK_RE.findall(html_text)
            ]
        seen: set[str] = set()
        for href, pid, raw_title in matches:
            url = (
                f"https://tieba.baidu.com{patch_href(href)}"
                if not href.startswith("http")
                else href
            )
            if pid and pid in seen:
                continue
            if pid:
                seen.add(pid)
            title = _strip_tags(raw_title)
            if not title:
                continue
            if any(kw in title for kw in self.keywords):
                result.append((title, url))
        logger.info(
            f"[{self.name}] 列表页解析出 {len(result)} 条避坑相关帖子"
            f"（关键词: {', '.join(self.keywords)}）"
        )
        return result

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """解析帖子首页：标题 + 首楼正文；反爬/登录标记 → 如实丢弃。"""
        parsed_items: list[dict] = []
        for raw in raw_items:
            url = raw.get("url", "")
            html_text = raw.get("html", "")
            if raw.get("status") != "ok" or not html_text:
                parsed_items.append(
                    {
                        "title": raw.get("title_hint", url),
                        "content": "",
                        "source_url": url,
                        "source_platform": "tieba",
                        "status": "failed",
                        "error": raw.get("error", "空响应"),
                    }
                )
                continue

            title = self._extract_title(html_text) or raw.get("title_hint") or url
            content = self._extract_content(html_text)

            if not content or any(marker in content for marker in _ANTI_CRAWL_MARKERS):
                logger.warning(f"[{self.name}] 帖子无正文或含登录/验证码墙，丢弃: {url}")
                parsed_items.append(
                    {
                        "title": title,
                        "content": "",
                        "source_url": url,
                        "source_platform": "tieba",
                        "status": "failed",
                        "error": "登录墙/验证码或空正文（合规跳过）",
                    }
                )
                continue

            parsed_items.append(
                {
                    "title": title,
                    "content": content,
                    "source_url": url,
                    "source_platform": "tieba",
                    "status": "ok",
                }
            )
        return parsed_items

    def _extract_title(self, html_text: str) -> str:
        match = _TITLE_RE.search(html_text)
        if match:
            title = _strip_tags(match.group(1))
            if title:
                return title
        return ""

    def _extract_content(self, html_text: str) -> str:
        """取首楼正文（d_post_content）；取不到返回空（如实丢弃）。"""
        match = _FLOOR_RE.search(html_text)
        if not match:
            return ""
        return _strip_tags(match.group(1))

    def store(self, items: list[dict], db=None) -> int:
        """将解析结果入库 t_external_research_item + t_review_queue_item。

        走 PENDING 审核队列，管理员确认后才落业务表（合规红线）。
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
                source_platform="tieba",
                run_id=str(run_record.id),
            )

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "forum": self.forum,
                "keywords": self.keywords,
                "pages": self.pages,
                "platform": "tieba",
            }
            db.commit()

            self.stats["stored"] = result["inserted"]
            self.stats["duplicates"] += result["duplicated"]

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

    # ------------------------------------------------------------------
    # CLI
    # ------------------------------------------------------------------


def patch_href(href: str) -> str:
    """列表页 href 可能带查询参数（如 ?pn=0），截断到 /p/ 帖子路径。"""
    if href.startswith("/p/"):
        return href.split("?")[0]
    return href


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="百度贴吧考研避坑帖调研爬虫")
    parser.add_argument("--forum", type=str, default="考研", help="贴吧名（默认：考研）")
    parser.add_argument(
        "--keywords", type=str, default="", help="避坑关键词，逗号分隔（缺省用默认集）"
    )
    parser.add_argument("--pages", type=int, default=1, help="列表页抓取页数（每页 50 帖）")
    parser.add_argument("--max-items", type=int, default=0, help="帖子抓取条数上限（0 不限）")
    args = parser.parse_args()

    config: dict = {"forum": args.forum, "pages": args.pages, "max_items": args.max_items}
    if args.keywords:
        config["keywords"] = [k.strip() for k in args.keywords.split(",") if k.strip()]
    crawler = TiebaResearchCrawler(config=config)
    result = crawler.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
