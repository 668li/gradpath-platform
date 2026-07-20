# -*- coding: utf-8 -*-
"""Firecrawl full crawl of kaoyan.com - uses scrape API for lower credit cost.

Targets: kaoyan.com (首页, experience, news, college, article pages)
Saves to: firecrawl_loop.json

Usage:
    python firecrawl_kaoyan_full.py
"""
import os
import sys
import json
import re
import time
import logging
import httpx
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "firecrawl_loop.json"


def clean_markdown(content: str) -> str:
    if not content:
        return ""
    text = re.sub(r'\{[^}]*\}', '', content)
    text = re.sub(r'/\*!.*?\*/', '', text)
    text = re.sub(r'--tw-[^:]+:[^;]+;', '', text)
    text = re.sub(r'\.tw-[^{]*\{[^}]*\}', '', text)
    text = re.sub(r'@media[^{]*\{[^}]*\}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    lines = content.split('\n')
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('{') or stripped.startswith('}') or stripped.startswith('/*'):
            continue
        if 'font-family' in stripped or 'font-size' in stripped:
            continue
        clean_lines.append(line)
    return '\n'.join(clean_lines).strip()


def classify_article(title: str, content: str) -> str:
    text = (title + " " + content).lower()
    kw_map = {
        "初试": ["初试", "笔试", "政治", "英语一", "数学一", "专业课"],
        "复试": ["复试", "面试"],
        "调剂": ["调剂", "调剂经验", "调剂指南"],
        "择校": ["择校", "选学校", "院校", "报考"],
        "备考": ["备考", "复习计划", "时间安排", "学习方法"],
        "政策": ["政策", "招生简章", "考试大纲", "报名"],
        "分数线": ["分数线", "国家线", "复试线", "录取线"],
        "专业分析": ["专业分析", "专业前景", "就业方向"],
        "院校信息": ["院校", "学校", "学院", "研究生院", "招生目录"],
    }
    for cat, keywords in kw_map.items():
        if any(kw in text for kw in keywords):
            return cat
    return "经验分享"


def extract_title_from_markdown(md: str) -> str:
    for line in md.split('\n'):
        stripped = line.strip()
        if stripped.startswith('# ') or stripped.startswith('## '):
            t = stripped.lstrip('# ').strip()
            if len(t) > 4 and not t.startswith('{') and not t.startswith('!'):
                return t[:200]
    return ""


def extract_article_urls_from_markdown(md: str, base_url: str = "https://www.kaoyan.com") -> list[str]:
    urls = []
    patterns = [
        r'\[([^\]]+)\]\((/article/[^\)]+)\)',
        r'\]\((https?://www\.kaoyan\.com/article/[^\)]+)\)',
        r'\]\((/article/\d+/\d+/[a-f0-9]+)\)',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, md):
            url = match.group(2) if match.lastindex == 2 else match.group(1)
            if url.startswith('/'):
                url = base_url + url
            if url.startswith('https://www.kaoyan.com/article/'):
                urls.append(url)
    return list(dict.fromkeys(urls))


def httpx_scrape(url: str, timeout: int = 30) -> str | None:
    """Fallback scraper using httpx."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.error(f"httpx failed for {url}: {e}")
        return None


def firecrawl_scrape_single(app, url: str) -> dict | None:
    """Scrape single page using Firecrawl scrape API."""
    try:
        result = app.scrape(url, formats=["markdown"])
        md = getattr(result, 'markdown', '') or ""
        return {"markdown": md, "url": url}
    except Exception as e:
        logger.error(f"Firecrawl scrape failed for {url}: {e}")
        return None


def parse_html_to_articles(html: str, url: str, section: str) -> list[dict]:
    """Parse HTML page to extract articles/links."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    articles = []

    # Find all links that look like articles
    for a_tag in soup.find_all("a", href=True):
        href = a_tag.get("href", "")
        text = a_tag.get_text(strip=True)

        if not text or len(text) < 5:
            continue

        # Article links
        if "/article/" in href:
            if href.startswith("/"):
                href = "https://www.kaoyan.com" + href
            articles.append({
                "title": text[:200],
                "url": href,
                "section": section,
            })
        # Category links
        elif any(seg in href for seg in ["/experience/", "/news/", "/college/", "/zhao/", "/fsx/", "/zhuanye/", "/tiaoji/"]):
            if href.startswith("/"):
                href = "https://www.kaoyan.com" + href
            articles.append({
                "title": text[:200],
                "url": href,
                "section": section,
            })

    return articles


def crawl_with_fallback(url: str, label: str, app=None) -> tuple[list[dict], list[str]]:
    """Crawl page with Firecrawl first, then httpx fallback."""
    articles = []
    discovered_urls = []

    # Try Firecrawl first
    if app:
        result = firecrawl_scrape_single(app, url)
        if result and result.get("markdown"):
            md = result["markdown"]
            title = extract_title_from_markdown(md)
            content = clean_markdown(md)
            category = classify_article(title, content)
            articles.append({
                "title": title[:200] if title else f"{label}页面",
                "url": url,
                "category": category,
                "content": content,
                "source": "kaoyan.com",
                "section": label,
                "scraped_at": datetime.now().isoformat(),
            })
            discovered_urls = extract_article_urls_from_markdown(md, url)
            return articles, discovered_urls

    # Fallback to httpx
    logger.info(f"  Using httpx fallback for {label}")
    html = httpx_scrape(url)
    if html:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        content = clean_markdown(text)

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else f"{label}页面"

        articles.append({
            "title": title[:200],
            "url": url,
            "category": classify_article(title, content),
            "content": content,
            "source": "kaoyan.com",
            "section": label,
            "scraped_at": datetime.now().isoformat(),
        })

        # Extract links
        link_data = parse_html_to_articles(html, url, label)
        discovered_urls = [l["url"] for l in link_data if "/article/" in l["url"]]

    return articles, discovered_urls


def main():
    print("=" * 60)
    print("Firecrawl 批量爬取 kaoyan.com 全部页面")
    print(f"API Key: {'已配置' if FIRECRAWL_API_KEY else '未配置'}")
    print("=" * 60)

    # Try to init Firecrawl
    app = None
    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
        print("  Firecrawl 客户端: 已初始化")
    except Exception as e:
        print(f"  Firecrawl 客户端: 初始化失败 ({e}), 使用 httpx 备选")

    all_articles = []
    seen_urls = set()

    crawl_targets = [
        ("首页", "https://www.kaoyan.com/"),
        ("经验", "https://www.kaoyan.com/experience/"),
        ("新闻", "https://www.kaoyan.com/news/"),
        ("院校", "https://www.kaoyan.com/college/"),
        ("招生", "https://www.kaoyan.com/zhao/"),
        ("分数线", "https://www.kaoyan.com/fsx/"),
        ("专业", "https://www.kaoyan.com/zhuanye/"),
        ("调剂", "https://www.kaoyan.com/tiaoji/"),
    ]

    all_discovered_urls = []

    for label, url in crawl_targets:
        articles, discovered = crawl_with_fallback(url, label, app)
        for a in articles:
            if a['url'] not in seen_urls:
                seen_urls.add(a['url'])
                all_articles.append(a)
        all_discovered_urls.extend(discovered)
        print(f"  [{label}] 获得 {len(articles)} 篇, 发现 {len(discovered)} 个链接")
        time.sleep(2)

    # Phase 2: Scrape discovered article pages
    unique_discovered = list(dict.fromkeys(all_discovered_urls))
    article_urls = [u for u in unique_discovered if '/article/' in u][:30]

    if article_urls:
        print(f"\n[文章详情] 爬取 {len(article_urls)} 篇文章详情 ...")
        count = 0
        for i, url in enumerate(article_urls):
            if url in seen_urls:
                continue

            # Try Firecrawl first
            article = None
            if app:
                result = firecrawl_scrape_single(app, url)
                if result and result.get("markdown"):
                    md = result["markdown"]
                    title = extract_title_from_markdown(md)
                    content = clean_markdown(md)
                    article = {
                        "title": title[:200] if title else "未命名文章",
                        "url": url,
                        "category": classify_article(title, content),
                        "content": content,
                        "source": "kaoyan.com",
                        "section": "article",
                        "scraped_at": datetime.now().isoformat(),
                    }

            # Fallback to httpx
            if not article:
                html = httpx_scrape(url)
                if html:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "html.parser")
                    text = soup.get_text(separator="\n", strip=True)
                    content = clean_markdown(text)
                    title_tag = soup.find("title")
                    title = title_tag.get_text(strip=True) if title_tag else "未命名文章"
                    article = {
                        "title": title[:200],
                        "url": url,
                        "category": classify_article(title, content),
                        "content": content,
                        "source": "kaoyan.com",
                        "section": "article",
                        "scraped_at": datetime.now().isoformat(),
                    }

            if article and len(article.get("content", "")) > 50:
                seen_urls.add(url)
                all_articles.append(article)
                count += 1

            if (i + 1) % 10 == 0:
                print(f"  进度: {i+1}/{len(article_urls)}, 成功: {count}")
            time.sleep(1.5)

        print(f"  文章详情: 获得 {count} 篇")

    # Save results
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_articles": len(all_articles),
        "total_chars": sum(len(a.get("content", "")) for a in all_articles),
        "articles": all_articles,
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    categories = {}
    sections = {}
    for a in all_articles:
        cat = a.get('category', 'unknown')
        sec = a.get('section', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1
        sections[sec] = sections.get(sec, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"爬取完成！")
    print(f"  总计: {len(all_articles)} 篇文章")
    print(f"  总字符数: {output['total_chars']:,}")
    print(f"  分类分布: {json.dumps(categories, ensure_ascii=False)}")
    print(f"  来源分布: {json.dumps(sections, ensure_ascii=False)}")
    print(f"  保存至: {OUTPUT_FILE}")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    main()
