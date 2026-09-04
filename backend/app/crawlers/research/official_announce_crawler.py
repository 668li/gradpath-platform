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

新增官方源 = 追加一节配置；CMS 结构不匹配既有正则模板时配 cms:"generic"
（通用列表解析：bs4 + 祖先链日期证据 + 同域护栏），正文由 trafilatura 优先抽取，
过短/失败自动降级原正则路径。
"""

import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

# 当以脚本形式从项目根目录运行时，把 backend 加入 sys.path
if __name__ == "__main__":
    backend_dir = Path(__file__).resolve().parents[3]
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

import html as html_lib

import trafilatura
from bs4 import BeautifulSoup
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


# 祖先链日期证据：2026年6月29日 / 2026-06-29 / 2026.6.29 / 2026/06/29 等
_DATE_EVIDENCE_RE = re.compile(r"(20\d{2})[年./\-](\d{1,2})[月./\-](\d{1,2})")


def parse_list_generic(html: str, base_url: str) -> list[dict]:
    """通用列表页解析（CMS 无关）：<a> 候选 + 祖先链日期证据 + 同域护栏。

    - 候选 = 带 href 的 <a>、文本 ≥6 字、urljoin 后与 base_url 同主机（忽略 www.）、
      scheme 为 http/https；
    - 日期证据：沿祖先链上溯 ≤4 级，第一个文本命中日期的祖先，归一化 YYYY-MM-DD；
      无日期 = 丢弃（导航/面包屑等噪声自然出局）；
    - 按 URL 去重、日期降序，返回 [{"url": 绝对URL, "title", "date"}]。
    """
    try:
        base_host = (urlparse(base_url).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return []
    if not base_host:
        return []
    soup = BeautifulSoup(html or "", "html.parser")
    seen: dict[str, dict] = {}
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if len(title) < 6:
            continue
        try:
            url = urljoin(base_url, a["href"].strip())
            parsed = urlparse(url)
        except ValueError:
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        host = (parsed.hostname or "").lower().removeprefix("www.")
        if host != base_host:
            continue
        date = ""
        node = a.parent
        for _ in range(4):
            if node is None:
                break
            m = _DATE_EVIDENCE_RE.search(node.get_text(" ", strip=True))
            if m:
                y, mo, d = m.groups()
                date = f"{y}-{int(mo):02d}-{int(d):02d}"
                break
            node = node.parent
        if not date:
            continue
        if url not in seen:
            seen[url] = {"url": url, "title": title, "date": date}
    return sorted(seen.values(), key=lambda e: e["date"], reverse=True)


def _parse_list_entries(html: str, template: str, base_url: str = "") -> list[dict]:
    """按栏目配置的 CMS 模板解析列表条目。template: boda（默认）| news_list | generic。"""
    if template == "generic":
        return parse_list_generic(html, base_url)
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


def extract_main_text(html: str) -> str:
    """trafilatura 正文抽取：中文连续无插空格、尾部不截断。

    异常 / None / len < _MIN_CONTENT_LEN 一律返回 ""，调用方降级原正则路径
    （短正文走原正则，与现状一致）。
    """
    try:
        text = trafilatura.extract(html, include_comments=False, favor_precision=True)
    except Exception:
        return ""
    if not text or len(text) < _MIN_CONTENT_LEN:
        return ""
    return text


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


def parse_detail_markdown(markdown: str) -> str:
    """把 crawl4ai 的结构化 markdown 转为纯文本（兼容 _extract_content_div 输出格式）。

    详情页经浏览器渲染后是干净的 markdown（# 标题、列表、加粗等），
    转纯文本后与 HTTP 正则抽取路径的输出形态一致，下游 summary/content 逻辑不变。
    """
    text = markdown or ""
    # 图片链接整段移除；普通链接保留可见文本
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # markdown 标题/列表/引用标记
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.M)
    text = re.sub(r"^\s*>\s*", "", text, flags=re.M)
    # 加粗/斜体/行内代码/代码块围栏
    text = re.sub(r"(\*\*|__|\*|_|`{1,3})", "", text)
    text = re.sub(r"^```.*$", "", text, flags=re.M)
    # 水平线
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.M)
    # 压缩多余空白/空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


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
        self._use_browser = bool(self.config.get("use_browser", False))
        # 并发窗口：config 显式设置并发时启用（默认 1 保持串行）。
        # 由 BaseCrawler 提供每线程独立 Session 与全局节流，网络限速不失效。
        self._concurrency = int(self.config.get("concurrency", 1))

    # ===== fetch：逐栏目抓列表 + 逐条详情（可选并发） =====

    def fetch(self) -> list[dict]:
        """遍历栏目：列表页条目 (title, url, date) → 详情页正文。

        并发>1 时对栏目做线程池并行（每个栏目内部仍串行抓列表+详情，
        避免对单一站点并发轰炸）；并发绝不触碰 robots 护栏（_request 保留
        SSRF/robots/重试/限速）。结果顺序不保证，调用方不依赖次序。
        """
        if self._concurrency <= 1 or len(self.sections) <= 1:
            raw_items: list[dict] = []
            for section in self.sections:
                raw_items.extend(self._fetch_section(section))
            return raw_items

        from concurrent.futures import ThreadPoolExecutor

        raw_items: list[dict] = []
        max_workers = min(self._concurrency, len(self.sections))
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(self._fetch_section, s) for s in self.sections]
            for fut in futures:
                try:
                    raw_items.extend(fut.result())
                except Exception as e:
                    self._bump_stats("errors")
                    logger.error(f"[{self.name}] 并发栏目抓取异常: {e}")
        return raw_items

    def _fetch_section(self, section: dict) -> list[dict]:
        """抓取单个栏目：列表页 → 逐条详情，返回条目数组（不抛未捕获异常）。"""
        collected: list[dict] = []
        list_url = section.get("list_url", "")
        if not list_url:
            return collected
        detail_re = re.compile(section.get("detail_url_re", r"\.htm$"))
        template = section.get("cms", "boda")
        try:
            resp = self._request(list_url)
            resp.encoding = "utf-8"
            section_items = 0
            for entry in _parse_list_entries(resp.text, template, list_url):
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
                collected.append(
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
            self._bump_stats("errors")
            logger.error(f"[{self.name}] 栏目 {list_url} 抓取失败: {e}")
        return collected

    def _fetch_detail(self, url: str, content_cls: str, title_suffix: str) -> tuple[str, str]:
        """抓取详情页，返回 (页面标题, 正文)；失败降级为列表信息。

        content_cls 为空时按常见 CMS 容器候选自动探测（新增栏目零配置成本）。
        HTTP 路径优先 trafilatura 抽取，未命中（异常/过短）再走 content_cls 正则
        或 auto-detect。
        use_browser=True 且 crawl4ai 可用时优先浏览器渲染（JS 渲染 + 结构化
        markdown），渲染失败/为空则降级当前 HTTP 正则抽取。
        """
        if self._use_browser:
            result = self.fetch_markdown(url)
            if result is not None and result.success and result.markdown:
                title = (result.title or "").strip()
                body = parse_detail_markdown(result.markdown)
                if body:
                    return title, body
                logger.warning(f"[{self.name}] crawl4ai markdown 为空，降级 HTTP: {url}")
        try:
            resp = self._request(url)
            resp.encoding = "utf-8"
            html = resp.text
            title = _title_from_html(html, title_suffix)
            # trafilatura 优先（干净完整正文）；为空降级原正则路径
            body = extract_main_text(html)
            if not body:
                if content_cls:
                    body = _extract_content_div(html, content_cls)
                else:
                    body = _auto_detect_content_cls(html)
            return title, body
        except Exception as e:
            self._bump_stats("errors")
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
