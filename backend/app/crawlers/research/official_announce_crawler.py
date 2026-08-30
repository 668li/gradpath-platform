"""官方公告爬虫 — 高校研招网 / 省级教育考试院公开公告。

Phase B2（合规边界内）：
- 只抓公开公告列表页 + 详情正文；robots 无限制或允许（高校 info 系统 / 考试院 CMS）
- 绝不触碰研招网 yz.chsi.com.cn（红线：数据不得对外分发）
- 官方域名（edu.cn / gov.cn）→ store_research_items 自动判为 official_verified
- 串行 + rate_limit，继承 BaseCrawler 页数/条数护栏

栏目配置驱动（OFFICIAL_SECTIONS）：每项
- name: 来源名称（用于展示与 source_meta）
- list_url: 公告列表页（结构：<li><a href="...htm">标题</a><span>日期</span></li>）
- detail_url_re: 详情链接必须匹配的相对路径正则（过滤 pdf/附件链接）
- content_cls: 详情页正文容器 class（如 v_news_content / TRS_Editor）
- title_suffix: <title> 标签需去除的后缀（如 "-华中农业大学研究生院"）

新增官方源 = 追加一节配置；校验：列表页 HTML 结构与 <li><a>+<span> 模式一致。
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
from app.services.research_ingestion import store_research_items

logger = logging.getLogger(__name__)

SOURCE_CHANNEL = "official_announce"

# 默认官方栏目：已实测验证（2026-08 抓取确认结构稳定）。
# 高校研招网公告是考研信息差核心权威源（调剂/复试线/考点公告）。
DEFAULT_SECTIONS: list[dict[str, Any]] = [
    {
        "name": "华中农业大学研究生院硕士招生",
        "list_url": "https://yjs.hzau.edu.cn/zsgz/sszs.htm",
        "detail_url_re": r"info/\d+/\d+\.htm",
        "content_cls": "v_news_content",
        "title_suffix": "-华中农业大学研究生院",
    },
    {
        # 2026-08-30 单校纵深实验发现的第二 CMS 模板（news_list）：
        # 苏州大学研究生院，正文容器 post-content（不在默认探测候选里，显式指定）
        "name": "苏州大学研究生院硕士招生",
        "list_url": "https://yjs.suda.edu.cn/8386/list.htm",
        "detail_url_re": r"/page\.htm$",
        "content_cls": "post-content",
        "cms": "news_list",
    },
]

# 通用列表条目：<li><a href="...htm">标题</a><span>YYYY-MM-DD</span></li>
_LIST_ITEM_RE = re.compile(
    r'<li><a href="(?P<url>[^"]+\.htm)">(?P<title>.*?)</a>'
    r"<span>(?P<date>\d{4}-\d{2}-\d{2})</span></li>",
    re.S,
)

# news-list-item 模板（苏州大学等 modern CMS）：
# <li class="news-list-item"><a href="URL" title="标题">…<span>日</span><b>YYYY.MM</b>…
_NEWS_LIST_ITEM_RE = re.compile(
    r'<li class="news-list-item">\s*<a href="(?P<url>[^"]+)" title="(?P<title>[^"]+)"'
    r".*?<span>(?P<day>\d{1,2})</span>\s*<b>(?P<year>\d{4})\.(?P<month>\d{1,2})</b>",
    re.S,
)


def _parse_list_entries(html: str, template: str) -> list[dict]:
    """按栏目配置的 CMS 模板解析列表条目。template: boda（默认）| news_list。"""
    entries: list[dict] = []
    if template == "news_list":
        for m in _NEWS_LIST_ITEM_RE.finditer(html):
            entries.append(
                {
                    "url": m.group("url"),
                    "title": m.group("title"),
                    "date": f"{m.group('year')}-{int(m.group('month')):02d}-{int(m.group('day')):02d}",
                }
            )
        return entries
    for m in _LIST_ITEM_RE.finditer(html):
        entries.append({"url": m.group("url"), "title": m.group("title"), "date": m.group("date")})
    return entries


def _extract_content_div(html: str, content_cls: str) -> str:
    """提取指定 class 的正文容器文本（兼容 class="x" 与 class=x 两种写法）。

    从容器 <div ...> 起到第一个闭合 </div>（高校正文容器通常无深嵌套）。
    """
    quoted = re.escape(content_cls)
    m = re.search(
        r'<div[^>]*class=["\']?' + quoted + r'["\']?[^>]*>(?P<body>.*?)</div>', html or "", re.S
    )
    if not m:
        return ""
    text = re.sub(r"<[^>]+>", " ", m.group("body"))
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# 常见高校 CMS 正文容器候选：新增栏目时 content_cls 可留空，按序自动探测
_CONTENT_CLS_CANDIDATES = [
    "v_news_content",
    "post-content",
    "TRS_Editor",
    "news_content",
    "article",
    "content",
    "zoom",
]

# 模板正文过短视为未命中（列表页摘要/空容器）
_MIN_CONTENT_LEN = 80


def _auto_detect_content_cls(html: str) -> str:
    """按候选序探测正文容器 class，返回第一个能取出足够文本的。"""
    for cls in _CONTENT_CLS_CANDIDATES:
        text = _extract_content_div(html, cls)
        if len(text) >= _MIN_CONTENT_LEN:
            return cls
    return ""


def _title_from_html(html: str, suffix: str = "") -> str:
    """从 <title> 标签提取标题，去掉站点后缀。"""
    m = re.search(r"<title>(.*?)</title>", html or "", re.S)
    if not m:
        return ""
    title = m.group(1).strip()
    if suffix and title.endswith(suffix):
        title = title[: -len(suffix)].strip()
    return title


@register_crawler
class OfficialAnnounceCrawler(BaseCrawler):
    """官方公告爬虫（高校研招网 / 省级考试院）。"""

    name = "official_announce"
    category = "research"
    description = "官方公告爬虫（高校研招网/省级考试院，edu.cn/gov.cn）"

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.sections = self.config.get("sections", DEFAULT_SECTIONS)
        self._rate_limit = self.config.get("rate_limit", 1.5)
        self.fetch_detail = bool(self.config.get("fetch_detail", True))

    # ===== fetch：逐栏目抓列表 + 逐条详情 =====

    def fetch(self) -> list[dict]:
        """遍历栏目：列表页条目 (title, url, date) → 详情页正文。"""
        raw_items: list[dict] = []
        for section in self.sections:
            list_url = section.get("list_url", "")
            if not list_url:
                continue
            detail_re = re.compile(section.get("detail_url_re", r"\.htm$"))
            template = section.get("cms", "boda")
            try:
                resp = self._request(list_url)
                resp.encoding = "utf-8"
                section_items = 0
                for entry in _parse_list_entries(resp.text, template):
                    href = entry["url"]
                    title = entry["title"]
                    date = entry["date"]
                    # 只收录匹配详情模式的条目（过滤 pdf/附件跳转）
                    if not detail_re.search(href):
                        continue
                    url = urljoin(list_url, href)
                    title = re.sub(r"\s+", " ", html_lib.unescape(title)).strip()
                    if not title or not url:
                        continue
                    detail_text = ""
                    detail_title = title
                    if self.fetch_detail:
                        detail_title, detail_text = self._fetch_detail(
                            url, section.get("content_cls", ""), section.get("title_suffix", "")
                        )
                    raw_items.append(
                        {
                            "title": detail_title or title,
                            "url": url,
                            "published_at": date,
                            "detail_text": detail_text,
                            "source_name": section.get("name", list_url),
                        }
                    )
                    section_items += 1
                logger.info(f"[{self.name}] 栏目 {section.get('name')} 解析 {section_items} 条")
            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"[{self.name}] 栏目 {list_url} 抓取失败: {e}")
        return raw_items

    def _fetch_detail(self, url: str, content_cls: str, title_suffix: str) -> tuple[str, str]:
        """抓取详情页，返回 (页面标题, 正文)；失败降级为列表信息。

        content_cls 为空时按常见 CMS 容器候选自动探测（新增栏目零配置成本）。
        """
        try:
            resp = self._request(url)
            resp.encoding = "utf-8"
            html = resp.text
            title = _title_from_html(html, title_suffix)
            if content_cls:
                body = _extract_content_div(html, content_cls)
            else:
                body = _auto_detect_content_cls(html)
            return title, body
        except Exception as e:
            self.stats["errors"] += 1
            logger.warning(f"[{self.name}] 详情页抓取失败，降级列表信息: {url} | {e}")
            return "", ""

    # ===== parse：复用 transformer 清洗/分类/质量分 =====

    def parse(self, raw_items: list[dict]) -> list[dict]:
        """转换为标准 KaoyanNews payload（复用 transform_rss 管线）。"""
        raw_payloads: list[dict] = []
        for raw in raw_items:
            title = raw.get("title", "")
            detail = raw.get("detail_text", "")
            summary = detail[:300] or title
            published_at = raw.get("published_at")
            raw_payloads.append(
                {
                    "title": title,
                    "summary": summary,
                    "content": detail or summary,
                    "source_url": raw.get("url", ""),
                    "published_at": published_at,
                    "crawled_at": datetime.now(timezone.utc).isoformat(),
                    "category": f"官方公告·{raw.get('source_name', '')}"[:50],
                    "tags": [],
                    "source_platform": "official",
                }
            )
        return ResearchTransformer.transform_rss(raw_payloads)

    # ===== store：CrawlerRun + 入库 =====

    def store(self, items: list[dict], db: Session = None) -> int:
        """入库 t_external_research_item + t_review_queue_item（PENDING 审核队列）。"""
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
                source_platform="official",
                run_id=str(run_record.id),
            )

            run_record.status = "success"
            run_record.items_fetched = self.stats.get("fetched", 0)
            run_record.items_stored = result["inserted"]
            run_record.items_duplicates = result["duplicated"]
            run_record.stored_count = result["inserted"]
            run_record.duplicate_count = result["duplicated"]
            run_record.source_meta = {
                "sections": [
                    {"name": s.get("name"), "list_url": s.get("list_url")} for s in self.sections
                ],
                "platform": "official",
            }
            db.commit()

            self.stats["stored"] = result["inserted"]
            self.stats["duplicates"] += result["duplicated"]
            logger.info(
                f"[{self.name}] 入库 {result['inserted']} 条新公告，去重 {result['duplicated']} 条"
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
    parser = argparse.ArgumentParser(description="官方公告爬虫 CLI")
    parser.add_argument("--no-detail", action="store_true", help="跳过详情页正文抓取")
    args = parser.parse_args()

    crawler = OfficialAnnounceCrawler(config={"fetch_detail": not args.no_detail})
    result = crawler.run()
    print(result)


if __name__ == "__main__":
    main()
