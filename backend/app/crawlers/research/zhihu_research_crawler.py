"""知乎公开专栏（zhuanlan）考研经验文章调研爬虫（Phase I）。

只抓取公开专栏文章（zhuanlan.zhihu.com/p/*）或专栏归档页，登录内容不爬：
- 正文解析后若含"登录后查看/安全验证"等反爬标记 → 如实丢弃（镜像 transform_web）
- robots.txt 不允许 / 获取失败 → fail-safe 跳过并如实记录 0 结果
- 入库走 store_research_items → PENDING 审核队列，人工确认后才落业务表
"""
import argparse
import html
import html.parser
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

# 反爬/登录拦截标记（命中即丢弃该条，如实记录，绝不绕过）
_ANTI_CRAWL_MARKERS = [
    "安全验证",
    "CAPTCHA",
    "please make sure you are authorized",
    "请您登录后查看",
    "登录后查看",
    "登录知乎",
]

_ARTICLE_LINK_RE = re.compile(r'href="(?:https?:)?//(?:zhuanlan\.)?zhihu\.com/p/(\d+)"')
# 标题：Post-Title 优先，回退 <title>（去掉 " - 知乎" 后缀）
_TITLE_RE = re.compile(r'<h1[^>]*class="[^"]*(?:Post-Title|ArticleHeader-Title)[^"]*"[^>]*>(.*?)</h1>', re.S)
_TITLE_TAG_RE = re.compile(r"<title>(.*?)</title>", re.S)


class _ZhuanlanTextExtractor(html.parser.HTMLParser):
    """提取 zhuanlan 文章正文容器（class=Post-RichTextContainer）内的可见文本。

    只收集容器内、非 script/style 块的文本；div 深度跟踪确定容器闭合，
    避免嵌套 div 提前截断。容器定位失败时 parts 为空，调用方如实丢弃。
    """

    def __init__(self):
        super().__init__()
        self._in_container = False
        self._div_depth = 0
        self._skip = False
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class") if attrs else None
        if not self._in_container and tag == "div" and classes and "Post-RichTextContainer" in classes.split():
            self._in_container = True
            self._div_depth = 1
            return
        if not self._in_container:
            return
        if tag in ("script", "style", "noscript", "svg", "iframe"):
            self._skip = True
        elif tag == "div":
            self._div_depth += 1
        elif tag in ("br", "p", "h1", "h2", "h3", "li", "blockquote", "tr", "hr"):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if not self._in_container:
            return
        if tag in ("script", "style", "noscript", "svg", "iframe"):
            self._skip = False
        elif tag == "div":
            if self._div_depth <= 1:
                self._in_container = False
            else:
                self._div_depth -= 1
        elif tag in ("p", "h1", "h2", "h3", "li", "blockquote"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_container and not self._skip:
            self.parts.append(data)


@register_crawler
class ZhihuResearchCrawler(BaseCrawler):
    """知乎公开专栏考研经验文章调研爬虫。"""

    name = "zhihu_research"
    category = "research"
    description = "知乎公开专栏（zhuanlan）考研经验文章调研爬虫"

    def __init__(self, config: dict = None):
        super().__init__(config)
        raw_seeds = self.config.get("seed_urls") or []
        if isinstance(raw_seeds, str):
            raw_seeds = raw_seeds.split(",")
        self.seed_urls = [u.strip() for u in raw_seeds if u.strip()]
        self.pages = int(self.config.get("pages", 1))
        # 基类按 _rate_limit 固定睡眠，这里自行控制 1-3 秒随机间隔（防风控）
        self._rate_limit = 0

    # ------------------------------------------------------------------
    # fetch → parse → store（基类 run 编排；store 走 PENDING 审核队列）
    # ------------------------------------------------------------------

    def fetch(self) -> list[dict]:
        """抓取 seed_urls 中的公开专栏文章（/p/*）或专栏归档页。"""
        if not self.seed_urls:
            return []
        raw_items: list[dict] = []
        article_urls: list[str] = []
        for seed in self.seed_urls:
            if self._is_article_url(seed):
                article_urls.append(seed)
                continue
            # 专栏/收藏夹归档页：解析其中的 /p/ 文章链接
            article_urls.extend(self._fetch_article_links(seed))
            time.sleep(random.uniform(1, 2))

        seen: set[str] = set()
        for url in article_urls:
            if url in seen:
                continue
            seen.add(url)
            try:
                resp = self._request(url, method="GET")
                raw_items.append({"url": url, "html": resp.text, "status": "ok"})
                logger.info(f"[{self.name}] 成功抓取: {url}")
            except Exception as e:
                logger.warning(f"[{self.name}] 抓取失败: {url} | {e}")
                raw_items.append({"url": url, "html": "", "status": "error", "error": str(e)})
            time.sleep(random.uniform(1, 3))
        return raw_items

    def _is_article_url(self, url: str) -> bool:
        return "/p/" in url

    def _fetch_article_links(self, archive_url: str) -> list[str]:
        """从专栏归档页解析 /p/ 文章链接（去重、限 max_pages 条）。"""
        try:
            resp = self._request(archive_url, method="GET")
        except Exception as e:
            logger.warning(f"[{self.name}] 归档页抓取失败: {archive_url} | {e}")
            return []
        matches = _ARTICLE_LINK_RE.findall(resp.text)
        links: list[str] = []
        seen: set[str] = set()
        for pid in matches:
            if pid in seen:
                continue
            seen.add(pid)
            links.append(f"https://zhuanlan.zhihu.com/p/{pid}")
        if self._max_pages > 0:
            links = links[: self._max_pages]
        logger.info(f"[{self.name}] 归档页 {archive_url} 解析出 {len(links)} 篇文章链接")
        return links

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """解析文章 HTML：标题 + 正文；反爬/登录标记 → 如实丢弃。"""
        parsed_items: list[dict] = []
        for raw in raw_items:
            url = raw.get("url", "")
            html_text = raw.get("html", "")
            if raw.get("status") != "ok" or not html_text:
                parsed_items.append({
                    "title": url,
                    "content": "",
                    "source_url": url,
                    "source_platform": "zhihu",
                    "status": "failed",
                    "error": raw.get("error", "空响应"),
                })
                continue

            title = self._extract_title(html_text) or url
            content = self._extract_content(html_text)

            if not content or any(marker in content for marker in _ANTI_CRAWL_MARKERS):
                logger.warning(f"[{self.name}] 文章无正文或含登录/验证码墙，丢弃: {url}")
                parsed_items.append({
                    "title": title,
                    "content": "",
                    "source_url": url,
                    "source_platform": "zhihu",
                    "status": "failed",
                    "error": "登录墙/验证码或空正文（合规跳过）",
                })
                continue

            parsed_items.append({
                "title": title,
                "content": content,
                "source_url": url,
                "source_platform": "zhihu",
                "status": "ok",
            })
        return parsed_items

    def _extract_title(self, html_text: str) -> str:
        match = _TITLE_RE.search(html_text)
        if match:
            title = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            if title:
                return title
        match = _TITLE_TAG_RE.search(html_text)
        if match:
            return html.unescape(match.group(1).strip().replace(" - 知乎", ""))
        return ""

    def _extract_content(self, html_text: str) -> str:
        extractor = _ZhuanlanTextExtractor()
        try:
            extractor.feed(html_text)
        except Exception:
            return ""
        text = "\n".join(extractor.parts)
        text = html.unescape(text)
        lines = [ln.strip() for ln in text.splitlines()]
        text = "\n".join(ln for ln in lines if ln)
        # 去掉「赞同/评论/收藏/分享/发布于/编辑于」等页面噪音行
        noise = re.compile(r"^(赞同\s*\d*|评论\s*\d*|收藏|分享|发布于\s|编辑于\s|广告\s*)$")
        kept = [ln for ln in text.splitlines() if not noise.match(ln)]
        return "\n".join(kept).strip()

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
                source_platform="zhihu",
                run_id=str(run_record.id),
            )

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "seed_urls": self.seed_urls,
                "platform": "zhihu",
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


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="知乎公开专栏考研经验文章调研爬虫")
    parser.add_argument(
        "--seed-urls",
        type=str,
        required=True,
        help="知乎公开专栏文章 URL 或专栏归档页 URL，逗号分隔",
    )
    parser.add_argument("--pages", type=int, default=1, help="归档页解析文章数上限（0 不限）")
    args = parser.parse_args()

    seeds = [u.strip() for u in args.seed_urls.split(",") if u.strip()]
    if not seeds:
        parser.error("--seed-urls 不能为空")

    crawler = ZhihuResearchCrawler(config={"seed_urls": seeds, "pages": args.pages})
    result = crawler.run()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
