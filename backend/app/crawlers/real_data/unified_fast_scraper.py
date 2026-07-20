# -*- coding: utf-8 -*-
"""统一高速爬取引擎 — 并发抓取多数据源，可选入库。

使用共享 httpx.AsyncClient + Semaphore 并发控制 + 429 指数退避重试，
统一调度研招网、考研帮、中公教育、华图教育四个数据源。
列表页发现 → 详情页抓取 → 可选数据库入库，全流程异步并行。

Usage:
    cd backend
    python -m app.crawlers.real_data.unified_fast_scraper --dry-run --limit 2
    python -m app.crawlers.real_data.unified_fast_scraper --source yanzhao --concurrency 20
    python -m app.crawlers.real_data.unified_fast_scraper --no-cache
"""
import sys
import json
import re
import os
import random
import logging
import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# ─── sys.path 处理（参考 firecrawl_import.py 模式）───
_backend_dir = Path(__file__).parent.parent.parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# ─── 从现有解析模块导入（均有 __name__ 保护，安全 import）───
# 注意：不从 fast_kaoyan_scraper.py 导入（其 asyncio.run 无 __name__ 保护）
try:
    from app.crawlers.real_data.firecrawl_yz_batch import extract_items_from_html
except ImportError:
    extract_items_from_html = None

try:
    from app.crawlers.real_data.firecrawl_kaoyan_full import (
        clean_markdown, classify_article, extract_title_from_markdown,
        parse_html_to_articles,
    )
except ImportError:
    clean_markdown = classify_article = None
    extract_title_from_markdown = parse_html_to_articles = None

try:
    from app.crawlers.real_data.civil_service_expand import (
        extract_links, extract_article_content,
    )
except ImportError:
    extract_links = extract_article_content = None

# ─── UA 轮换池（复用 real_data_crawler.py 的 6 个 UA）───
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

_MODULE_DIR = Path(__file__).parent
_SOURCES_FILE = _MODULE_DIR / "sources.yaml"
_CACHE_FILE = _MODULE_DIR / ".url_cache.json"
_OUTPUT_FILE = _MODULE_DIR / "unified_scrape_results.json"


# ═══════════════════════════════════════════════════════════════
# pyyaml 可能未安装 — try/except 回退到 Python dict 常量配置
# ═══════════════════════════════════════════════════════════════

def _gen_yz_list_urls() -> list[str]:
    """根据 firecrawl_yz_batch.py 的 SECTIONS 配置生成实际 URL 列表。

    page 1  → {BASE_URL}{path}
    page 2+ → {BASE_URL}{path}index_{page}.html
    """
    urls = []
    for path, pages in [("/kyzx/kydt/", 5), ("/kyzx/jybzc/", 3),
                         ("/kyzx/zsjz/", 3), ("/kyzx/fstj/", 3)]:
        for p in range(1, pages + 1):
            if p == 1:
                urls.append(f"https://yz.chsi.com.cn{path}")
            else:
                urls.append(f"https://yz.chsi.com.cn{path}index_{p}.html")
    return urls


# 内置回退配置 — 当 pyyaml 不可用或 sources.yaml 加载失败时使用
_FALLBACK_SOURCES = {
    "yanzhao": {
        "name": "研招网", "enabled": True, "source_type": "grad",
        "list_urls": _gen_yz_list_urls(),
        "list_parser": "yz_list", "detail_parser": "yz_detail",
        "concurrency": 10, "rate_limit": 0.5,
        "target_model": "ExperiencePost", "unique_key": "source_url",
        "category_map": {"kydt": "政策", "jybzc": "政策", "zsjz": "政策", "fstj": "复试"},
    },
    "kaoyan": {
        "name": "考研帮", "enabled": True, "source_type": "grad",
        "list_urls": [
            "https://www.kaoyan.com/experience/?page=1",
            "https://www.kaoyan.com/experience/?page=2",
            "https://www.kaoyan.com/experience/?page=3",
            "https://www.kaoyan.com/experience/?page=4",
            "https://www.kaoyan.com/experience/?page=5",
            "https://www.kaoyan.com/news/list/1/9370",
            "https://www.kaoyan.com/news/list/1/3946",
            "https://www.kaoyan.com/news/list/1/3949",
        ],
        "list_parser": "kaoyan_list", "detail_parser": "kaoyan_detail",
        "concurrency": 15, "rate_limit": 0.3,
        "target_model": "ExperiencePost", "unique_key": "source_url",
        "category_map": {"初试": "初试", "复试": "复试", "调剂": "调剂",
                          "择校": "择校", "备考": "复习", "政策": "general",
                          "分数线": "初试", "经验分享": "general"},
    },
    "offcn": {
        "name": "中公教育", "enabled": True, "source_type": "civil",
        "list_urls": [
            "https://www.offcn.com/gwy/", "https://www.offcn.com/sksy/",
            "https://www.offcn.com/xd/", "https://www.offcn.com/shiyedanwei/",
        ],
        "list_parser": "offcn_list", "detail_parser": "offcn_detail",
        "concurrency": 8, "rate_limit": 0.5,
        "target_model": "ExperiencePost", "unique_key": "source_url",
        "category_map": {"国考": "general", "省考": "general",
                          "选调": "general", "事业单位": "general"},
    },
    "huatu": {
        "name": "华图教育", "enabled": True, "source_type": "civil",
        "list_urls": [
            "https://www.huatu.com/guojia/", "https://www.huatu.com/sheng/",
            "https://www.huatu.com/xds/", "https://www.huatu.com/sydw/",
        ],
        "list_parser": "huatu_list", "detail_parser": "huatu_detail",
        "concurrency": 8, "rate_limit": 0.5,
        "target_model": "ExperiencePost", "unique_key": "source_url",
        "category_map": {"国考": "general", "省考": "general",
                          "选调": "general", "事业单位": "general"},
    },
    "sina_edu": {
        "name": "新浪教育", "enabled": True, "source_type": "news",
        "list_urls": [
            "https://edu.sina.com.cn/",
            "https://edu.sina.com.cn/kaoyan/",
            "https://edu.sina.com.cn/gaokao/",
            "https://edu.sina.com.cn/zt_d/kaoyan/",
        ],
        "list_parser": "sina_list", "detail_parser": "generic_detail",
        "concurrency": 10, "rate_limit": 0.3,
        "target_model": "ExperiencePost", "unique_key": "source_url",
        "category_map": {"kaoyan": "general", "gaokao": "general", "study_abroad": "general"},
    },
    "moe": {
        "name": "教育部", "enabled": False, "source_type": "policy",
        "list_urls": [
            "http://www.moe.gov.cn/jyb_xwfb/",
            "http://www.moe.gov.cn/jyb_xwfb/xw_zt/",
            "http://www.moe.gov.cn/jyb_xxgk/jyb_xxgk_tjzl/",
        ],
        "list_parser": "moe_list", "detail_parser": "generic_detail",
        "concurrency": 5, "rate_limit": 0.8,
        "target_model": "ExperiencePost", "unique_key": "source_url",
        "category_map": {"政策": "policy", "通知": "policy", "公告": "policy"},
    },
    "xinhua_edu": {
        "name": "新华网教育", "enabled": True, "source_type": "news",
        "list_urls": [
            "http://www.xinhuanet.com/edu/",
            "http://www.xinhuanet.com/edu/2026-07/",
        ],
        "list_parser": "xinhua_list", "detail_parser": "generic_detail",
        "concurrency": 8, "rate_limit": 0.5,
        "target_model": "ExperiencePost", "unique_key": "source_url",
        "category_map": {"教育": "general", "考研": "general", "高教": "general"},
    },
    "eol": {
        "name": "中国教育在线", "enabled": True, "source_type": "news",
        "list_urls": [
            "https://www.eol.cn/kaoyan/",
            "https://www.eol.cn/kaoyan/zhengce/",
            "https://www.eol.cn/kaoyan/kyzx/",
        ],
        "list_parser": "eol_list", "detail_parser": "generic_detail",
        "concurrency": 8, "rate_limit": 0.5,
        "target_model": "ExperiencePost", "unique_key": "source_url",
        "category_map": {"考研": "general", "政策": "policy", "资讯": "general"},
    },
}


def load_sources() -> dict:
    """加载 sources.yaml；pyyaml 不可用时回退到 _FALLBACK_SOURCES。"""
    try:
        import yaml
        if _SOURCES_FILE.exists():
            with open(_SOURCES_FILE, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data and isinstance(data, dict):
                return data
    except ImportError:
        logger.info("pyyaml 未安装，使用内置配置常量")
    except Exception as e:
        logger.warning(f"加载 sources.yaml 失败 ({e})，使用内置配置常量")
    return _FALLBACK_SOURCES


# ═══════════════════════════════════════════════════════════════
# 详情页解析函数 — 统一签名 (html: str, url: str) -> dict
# ═══════════════════════════════════════════════════════════════

def _parse_yz_detail(html: str, url: str) -> dict:
    """解析研招网详情页 — 提取标题和正文文本。"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    content = re.sub(r'\n{3,}', '\n\n', text).strip()[:5000]
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else "研招网文章"
    return {"title": title[:200], "content": content, "category": "政策",
            "source": "yz.chsi.com.cn", "url": url,
            "scraped_at": datetime.now().isoformat()}


def _parse_kaoyan_detail(html: str, url: str) -> dict:
    """解析考研帮详情页 — 复用 clean_markdown/classify_article。"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n", strip=True)
    content = clean_markdown(text) if clean_markdown else text
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""
    if not title and extract_title_from_markdown:
        title = extract_title_from_markdown(text)
    if not title:
        title = "考研帮文章"
    category = classify_article(title, content) if classify_article else "经验分享"
    return {"title": title[:200], "content": content[:5000], "category": category,
            "source": "kaoyan.com", "url": url,
            "scraped_at": datetime.now().isoformat()}


def _parse_civil_detail(html: str, url: str) -> dict:
    """解析中公/华图详情页 — 复用 extract_article_content。"""
    content = extract_article_content(html) if extract_article_content else ""
    if not content or len(content) < 30:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        content = soup.get_text(separator="\n", strip=True)[:5000]
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.DOTALL)
    title = m.group(1).strip() if m else "公考资讯"
    return {"title": title[:200], "content": content[:5000], "category": "公考",
            "source": "civil_service", "url": url,
            "scraped_at": datetime.now().isoformat()}


def _parse_generic_list(html: str, url: str, domain_keywords: list = None) -> list[dict]:
    """通用列表页解析器 — 从HTML中提取所有文章链接。

    根据域名关键词判断链接是否属于本站，并过滤导航/广告链接。
    """
    from urllib.parse import urlparse, urljoin
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    base_domain = urlparse(url).netloc
    if not domain_keywords:
        domain_keywords = [base_domain.split(".")[0]]

    skip_nav = {"首页", "登录", "注册", "更多", ">>", "关于我们", "联系我们",
                "设为首页", "收藏", "APP下载", "客服", "返回", "上一页", "下一页"}
    seen = set()
    results = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        title = a.get_text(strip=True)

        if len(title) < 6 or len(title) > 150:
            continue
        if any(skip in title for skip in skip_nav):
            continue

        # Normalize URL
        if href.startswith("//"):
            href = "https:" + href
        if not href.startswith("http"):
            href = urljoin(url, href)

        parsed = urlparse(href)
        # Must be same domain or subdomain
        if not any(kw in parsed.netloc for kw in domain_keywords):
            continue
        # Skip non-article resources
        path = parsed.path.lower()
        if any(ext in path for ext in [".css", ".js", ".png", ".jpg", ".gif", ".ico", ".svg", ".pdf"]):
            continue
        # Skip very short paths (homepage, section roots)
        if not path or path == "/" or path.count("/") <= 1:
            continue
        if href in seen:
            continue
        seen.add(href)
        results.append({"title": title, "url": href})

    return results


def _parse_generic_detail(html: str, url: str) -> dict:
    """通用详情页解析器 — 提取标题和正文，自动识别来源域名。"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")

    # Remove script/style
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Extract title
    title = ""
    # Try og:title first
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    if not title:
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)
    if not title:
        title = "教育资讯"

    # Extract content from article/main area
    content_el = soup.find("article") or soup.find("div", class_=re.compile(r"article|content|post|body|main")) or soup.find("main")
    if content_el:
        content = content_el.get_text(separator="\n", strip=True)
    else:
        content = soup.get_text(separator="\n", strip=True)

    content = re.sub(r'\n{3,}', '\n\n', content).strip()[:5000]

    # Determine source from URL
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    source_map = {
        "sina.com.cn": "sina.edu.cn",
        "moe.gov.cn": "moe.gov.cn",
        "xinhuanet.com": "xinhuanet.com",
        "eol.cn": "eol.cn",
        "fenbi.com": "fenbi.com",
        "hqwx.com": "hqwx.com",
        "163.com": "163.edu",
        "netease.com": "163.edu",
        "sohu.com": "sohu.edu",
        "chsi.com.cn": "gaokao.chsi.com.cn",
    }
    source = next((v for k, v in source_map.items() if k in domain), domain)

    # Auto-classify category
    category = "教育资讯"
    text_lower = (title + content).lower()
    if any(kw in text_lower for kw in ["考研", "研究生", "招生", "复试", "调剂"]):
        category = "考研"
    elif any(kw in text_lower for kw in ["公务员", "国考", "省考", "选调", "事业单位", "事业编", "事业编制"]):
        category = "考公"
    elif any(kw in text_lower for kw in ["就业", "招聘", "薪资", "面试", "简历", "求职"]):
        category = "就业"
    elif any(kw in text_lower for kw in ["教师", "教资", "教师资格", "教招", "教师招聘"]):
        category = "教师"
    elif any(kw in text_lower for kw in ["建造", "造价", "消防", "注册", "执业资格"]):
        category = "职业资格"
    elif any(kw in text_lower for kw in ["政策", "通知", "公告", "意见"]):
        category = "政策"

    return {"title": title[:200], "content": content, "category": category,
            "source": source, "url": url,
            "scraped_at": datetime.now().isoformat()}


# ═══════════════════════════════════════════════════════════════
# PARSE_REGISTRY — 注册现有解析函数，用 lambda 统一签名 (html, url)
# 列表解析器: (html, url) -> list[dict]  (每项含 url/title)
# 详情解析器: (html, url) -> dict        (含 title/content/category/source/url)
# ═══════════════════════════════════════════════════════════════

PARSE_REGISTRY = {
    # 列表页解析器 — 用 lambda 适配不同签名的现有函数
    "yz_list": lambda html, url: (
        extract_items_from_html(html, "default") if extract_items_from_html else []
    ),
    "kaoyan_list": lambda html, url: (
        parse_html_to_articles(html, url, "kaoyan") if parse_html_to_articles else []
    ),
    "offcn_list": lambda html, url: (
        extract_links(html, url) if extract_links else []
    ),
    "huatu_list": lambda html, url: (
        extract_links(html, url) if extract_links else []
    ),
    # 新增通用列表解析器
    "sina_list": lambda html, url: _parse_generic_list(html, url, ["sina.com.cn"]),
    "moe_list": lambda html, url: _parse_generic_list(html, url, ["moe.gov.cn"]),
    "xinhua_list": lambda html, url: _parse_generic_list(html, url, ["xinhuanet.com", "新华网"]),
    "eol_list": lambda html, url: _parse_generic_list(html, url, ["eol.cn"]),
    "eol_kaoyan_list": lambda html, url: _parse_generic_list(html, url, ["eol.cn", "kaoyan.eol.cn", "kaoyan.cn"]),
    "fenbi_list": lambda html, url: _parse_generic_list(html, url, ["fenbi.com"]),
    "hqwx_list": lambda html, url: _parse_generic_list(html, url, ["hqwx.com"]),
    "163_edu_list": lambda html, url: _parse_generic_list(html, url, ["163.com", "netease.com"]),
    "sohu_edu_list": lambda html, url: _parse_generic_list(html, url, ["sohu.com"]),
    "gaokao_cn_list": lambda html, url: _parse_generic_list(html, url, ["chsi.com.cn", "gaokao"]),
    "eol_gaokao_list": lambda html, url: _parse_generic_list(html, url, ["eol.cn", "gaokao"]),
    "51job_list": lambda html, url: _parse_generic_list(html, url, ["51job.com", "jobui.com"]),
    "boss_list": lambda html, url: _parse_generic_list(html, url, ["zhipin.com", "bosszhipin"]),
    "eol_college_list": lambda html, url: _parse_generic_list(html, url, ["eol.cn", "gaokao"]),
    "mofangge_list": lambda html, url: _parse_generic_list(html, url, ["mofangge.com"]),
    "mofangge_eng_list": lambda html, url: _parse_generic_list(html, url, ["mofangge.com", "gongcheng", "jiaoyu", "english"]),
    # 详情页解析器 — 已统一签名
    "yz_detail": _parse_yz_detail,
    "kaoyan_detail": _parse_kaoyan_detail,
    "offcn_detail": _parse_civil_detail,
    "huatu_detail": _parse_civil_detail,
    "generic_detail": _parse_generic_detail,
}


# ═══════════════════════════════════════════════════════════════
# URLCache — 内存 set + 本地 JSON 文件缓存
# ═══════════════════════════════════════════════════════════════

class URLCache:
    """两级缓存：内存 set 快速判断 + JSON 文件持久化。"""

    def __init__(self, cache_file: str | Path = None):
        self._mem: set[str] = set()
        self._file = str(cache_file or _CACHE_FILE)
        self._load()

    def _load(self):
        if os.path.exists(self._file):
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    self._mem = set(json.load(f))
            except Exception:
                pass

    def has(self, url: str) -> bool:
        return url in self._mem

    def add(self, url: str):
        self._mem.add(url)

    def add_many(self, urls):
        self._mem.update(urls)

    def save(self):
        try:
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(list(self._mem), f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"缓存保存失败: {e}")

    def __len__(self):
        return len(self._mem)


# ═══════════════════════════════════════════════════════════════
# robots.txt 检查 — 按域名缓存 RobotFileParser 结果（参考 fetcher.py）
# ═══════════════════════════════════════════════════════════════

_robots_cache: dict[str, RobotFileParser | bool] = {}


def check_robots_allowed(url: str, user_agent: str = "*") -> bool:
    """检查 robots.txt 是否允许抓取指定 URL，按域名缓存结果。

    fail-closed：无法读取 robots.txt 时默认禁止（与 fetcher.py 一致）。
    """
    parsed = urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    if domain in _robots_cache:
        cached = _robots_cache[domain]
        if isinstance(cached, bool):
            return cached
        return cached.can_fetch(user_agent, url)
    try:
        rp = RobotFileParser()
        rp.set_url(f"{domain}/robots.txt")
        rp.read()
        _robots_cache[domain] = rp
        return rp.can_fetch(user_agent, url)
    except Exception:
        _robots_cache[domain] = False
        return False


# ═══════════════════════════════════════════════════════════════
# async discover_urls — 并发抓列表页，提取详情 URL
# ═══════════════════════════════════════════════════════════════

async def discover_urls(
    client: httpx.AsyncClient,
    config: dict,
    cache: URLCache | None,
    limit: int | None = None,
) -> list[str]:
    """并发抓取列表页，用注册的 list_parser 提取详情页 URL。"""
    list_urls = config.get("list_urls", [])
    parser = PARSE_REGISTRY.get(config.get("list_parser", ""))
    concurrency = config.get("concurrency", 10)
    rate_limit = config.get("rate_limit", 0.3)
    sem = asyncio.Semaphore(concurrency)
    found: list[str] = []

    async def fetch_list(url: str) -> list[str]:
        async with sem:
            if not check_robots_allowed(url):
                logger.info(f"[robots] 禁止抓取: {url}")
                return []
            await asyncio.sleep(rate_limit)
            try:
                resp = await client.get(
                    url,
                    headers={"User-Agent": random.choice(_USER_AGENTS)},
                    follow_redirects=True, timeout=20,
                )
                if resp.status_code == 200:
                    items = parser(resp.text, url) if parser else []
                    return [it.get("url", "") for it in items if it.get("url")]
            except Exception as e:
                logger.warning(f"列表页抓取失败 {url}: {e}")
            return []

    tasks = [fetch_list(u) for u in list_urls]
    results = await asyncio.gather(*tasks)
    for urls in results:
        for u in urls:
            if u and u not in found:
                if cache is not None and cache.has(u):
                    continue
                found.append(u)
    if limit:
        found = found[:limit]
    return found


# ═══════════════════════════════════════════════════════════════
# async crawl_source — Semaphore 控制并发抓详情页，含 429 指数退避重试
# ═══════════════════════════════════════════════════════════════

async def crawl_source(
    client: httpx.AsyncClient,
    config: dict,
    urls: list[str],
    cache: URLCache | None,
) -> list[dict]:
    """并发抓取详情页，用注册的 detail_parser 解析内容。"""
    parser = PARSE_REGISTRY.get(config.get("detail_parser", ""))
    concurrency = config.get("concurrency", 10)
    sem = asyncio.Semaphore(concurrency)
    articles: list[dict] = []

    async def fetch_detail(url: str) -> dict | None:
        async with sem:
            if not check_robots_allowed(url):
                return None
            for attempt in range(3):
                try:
                    resp = await client.get(
                        url,
                        headers={"User-Agent": random.choice(_USER_AGENTS)},
                        follow_redirects=True, timeout=20,
                    )
                    if resp.status_code == 200:
                        article = parser(resp.text, url) if parser else None
                        if article and article.get("content", "").strip():
                            if cache is not None:
                                cache.add(url)
                            return article
                        return None
                    elif resp.status_code == 429:
                        # 429 指数退避重试：2^random(1,3) 秒
                        delay = 2 ** random.randint(1, 3)
                        logger.warning(f"[429] 限流，等待 {delay}s 后重试: {url}")
                        await asyncio.sleep(delay)
                        continue
                    return None
                except (httpx.TimeoutException, httpx.ConnectError) as e:
                    delay = 2 ** (attempt + 1) + random.uniform(0, 1)
                    logger.warning(f"请求失败({attempt+1}/3): {e}, {delay:.1f}s 后重试")
                    await asyncio.sleep(delay)
                except Exception as e:
                    logger.error(f"详情页抓取异常 {url}: {e}")
                    return None
            return None

    tasks = [fetch_detail(u) for u in urls]
    results = await asyncio.gather(*tasks)
    for a in results:
        if a:
            articles.append(a)
    return articles


# ═══════════════════════════════════════════════════════════════
# async run_all — 单个 httpx.AsyncClient 共享，顶层 asyncio.gather 并行所有源
# ═══════════════════════════════════════════════════════════════

async def run_all(args) -> dict:
    """运行全部启用数据源：发现 URL → 抓取详情页。"""
    sources = load_sources()
    if args.source and args.source != "all":
        sources = {k: v for k, v in sources.items() if k == args.source}

    # 覆盖并发数
    if args.concurrency:
        for cfg in sources.values():
            cfg["concurrency"] = args.concurrency

    cache = None if args.no_cache else URLCache()
    # httpx.Limits 配置：max_connections=50, max_keepalive_connections=20
    limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
    all_results: dict[str, dict] = {}

    active = [(name, cfg) for name, cfg in sources.items() if cfg.get("enabled", True)]
    logger.info("=" * 60)
    logger.info(f"统一高速爬取引擎 — 活跃源: {[n for n, _ in active]}")
    logger.info("=" * 60)

    # 整个 run_all 共享一个 httpx.AsyncClient 实例（连接复用）
    async with httpx.AsyncClient(limits=limits, follow_redirects=True) as client:

        async def run_one(name: str, cfg: dict) -> dict:
            logger.info(f"[{name}] 开始 — 列表页 {len(cfg.get('list_urls', []))} 个")
            urls = await discover_urls(client, cfg, cache, limit=args.limit)
            logger.info(f"[{name}] 发现 {len(urls)} 个详情 URL")
            if args.dry_run:
                logger.info(f"[{name}] --dry-run 模式，跳过详情抓取")
                for u in urls[:5]:
                    logger.info(f"    -> {u}")
                return {"discovered": len(urls), "articles": []}
            articles = await crawl_source(client, cfg, urls, cache)
            logger.info(f"[{name}] 完成 — 成功抓取 {len(articles)} 篇文章")
            return {"discovered": len(urls), "articles": articles}

        # 顶层 asyncio.gather 并行所有源
        tasks = [run_one(name, cfg) for name, cfg in active]
        results = await asyncio.gather(*tasks)
        for (name, _), result in zip(active, results):
            all_results[name] = result

    if cache is not None and not args.dry_run:
        cache.save()

    # 保存结果到 JSON
    total_articles = sum(len(r.get("articles", [])) for r in all_results.values())
    total_discovered = sum(r.get("discovered", 0) for r in all_results.values())
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_discovered": total_discovered,
        "total_articles": total_articles,
        "sources": {
            k: {"discovered": v["discovered"], "articles": v["articles"]}
            for k, v in all_results.items()
        },
    }
    _OUTPUT_FILE.write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("=" * 60)
    logger.info(f"全部完成 — 发现 {total_discovered} URL, 抓取 {total_articles} 篇文章")
    logger.info(f"结果保存至: {_OUTPUT_FILE}")
    logger.info("=" * 60)
    return all_results


# ═══════════════════════════════════════════════════════════════
# import_to_db — 同步入库，db.add_all() + commit（跨方言兼容）
# 不使用 base_crawler.batch_upsert（pg_insert 在 SQLite 上不兼容）
# ═══════════════════════════════════════════════════════════════

def import_to_db(all_results: dict) -> int:
    """将抓取的文章导入数据库 ExperiencePost 表。"""
    import uuid
    from sqlalchemy import select
    from app.database import Base, SessionLocal, engine
    from app.models.user import User
    from app.models.experience_post import ExperiencePost

    SEED_EMAIL = "unified_scraper@gradpath.local"
    SEED_NAME = "统一爬取引擎"

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 获取或创建种子用户
        user = db.execute(
            select(User).where(User.email == SEED_EMAIL)
        ).scalars().first()
        if not user:
            user = User(
                id=uuid.uuid4(), email=SEED_EMAIL, name=SEED_NAME,
                password_hash="not_a_real_password", is_admin=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"创建种子用户: {SEED_NAME} ({user.id})")

        # 获取已存在的 source_url（去重，参考 base_crawler.get_existing_keys 模式）
        existing = {
            row[0] for row in db.execute(
                select(ExperiencePost.source_url).where(
                    ExperiencePost.source_url.isnot(None)
                )
            ).all()
        }
        logger.info(f"数据库中已有 {len(existing)} 篇经验帖")

        # 收集所有文章
        all_articles = []
        for result in all_results.values():
            all_articles.extend(result.get("articles", []))
        logger.info(f"待入库文章: {len(all_articles)} 篇")

        # 构建 ExperiencePost 对象（db.add_all + commit，与 firecrawl_import.py 一致）
        new_posts = []
        for article in all_articles:
            url = article.get("url", "")
            if url in existing:
                continue
            content = article.get("content", "")
            if len(content) < 50:
                content = f"{article.get('title', '')}\n\n{content}\n\n原文链接: {url}"
            summary = content[:200].replace("\n", " ").strip()
            if len(summary) > 197:
                summary = summary[:197] + "..."
            post = ExperiencePost(
                id=uuid.uuid4(), user_id=user.id,
                title=article.get("title", "未命名文章")[:200],
                summary=summary, content=content,
                tags=[article.get("category", ""), article.get("source", ""), "unified_scraper"],
                category=article.get("category", "general"),
                view_count=0, like_count=0, comment_count=0,
                external_view_count=0, external_like_count=0,
                is_pinned=False, is_anonymous=False, status="approved",
                source_platform="crawler", source_url=url, is_verified=True,
            )
            new_posts.append(post)
            existing.add(url)

        if new_posts:
            db.add_all(new_posts)
            db.commit()
        logger.info(f"入库完成: 新增 {len(new_posts)} 篇经验帖")
        return len(new_posts)
    except Exception as e:
        db.rollback()
        logger.error(f"入库失败: {e}")
        logger.exception("入库失败详情")
        return 0
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="统一高速爬取引擎")
    parser.add_argument("--source", default="all",
                        help="数据源名称 (yanzhao/kaoyan/offcn/huatu/all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅发现 URL，不抓取详情页")
    parser.add_argument("--concurrency", type=int, default=None,
                        help="覆盖默认并发数")
    parser.add_argument("--limit", type=int, default=None,
                        help="每个源最多抓取的详情页数")
    parser.add_argument("--no-cache", action="store_true",
                        help="禁用 URL 缓存")
    parser.add_argument("--no-import", action="store_true",
                        help="跳过数据库入库")
    args = parser.parse_args()

    # argparse 解析 → asyncio.run(run_all())
    all_results = asyncio.run(run_all(args))

    # 可选 import_to_db()
    if not args.dry_run and not args.no_import:
        logger.info("=" * 60)
        logger.info("开始入库...")
        import_to_db(all_results)


if __name__ == "__main__":
    main()
