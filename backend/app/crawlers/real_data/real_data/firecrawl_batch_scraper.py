# -*- coding: utf-8 -*-
"""Batch scrape real graduate school articles using Firecrawl.

Targets: kaoyan.com, yz.chsi.com.cn
Saves to: firecrawl_scraped.json

Usage:
    python -m app.crawlers.real_data.firecrawl_batch_scraper
"""
import os
import sys
import json
import re
import time
import logging
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "firecrawl_scraped.json"


def clean_markdown(content: str) -> str:
    """Remove CSS noise and clean markdown content."""
    if not content:
        return ""
    text = re.sub(r'\{[^}]*\}', '', content)
    text = re.sub(r'/\*!.*?\*/', '', text)
    text = re.sub(r'--tw-[^:]+:[^;]+;', '', text)
    text = re.sub(r'\.tw-[^{]*\{[^}]*\}', '', text)
    text = re.sub(r'@media[^{]*\{[^}]*\}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    lines = text.split('\n')
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
    """Classify article category based on title and content."""
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
    }
    for cat, keywords in kw_map.items():
        if any(kw in text for kw in keywords):
            return cat
    return "经验分享"


def extract_title_from_markdown(md: str) -> str:
    """Extract title from markdown content."""
    for line in md.split('\n'):
        stripped = line.strip()
        if stripped.startswith('# ') or stripped.startswith('## '):
            t = stripped.lstrip('# ').strip()
            if len(t) > 4 and not t.startswith('{') and not t.startswith('!'):
                return t[:200]
    return ""


def crawl_kaoyan_batch():
    """Use Firecrawl crawl API to get pages from kaoyan.com."""
    from firecrawl import FirecrawlApp

    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    all_articles = []
    seen_urls = set()

    # Crawl main page and category pages
    targets = [
        "https://www.kaoyan.com/",
        "https://www.kaoyan.com/zhao/",
    ]

    for target_url in targets:
        logger.info(f"Crawling: {target_url}")
        try:
            result = app.crawl(
                target_url,
                limit=25,
                scrape_options={"formats": ["markdown"]},
            )

            if not hasattr(result, 'data') or not result.data:
                logger.warning(f"  No data from {target_url}")
                time.sleep(3)
                continue

            pages = result.data
            logger.info(f"  Got {len(pages)} pages")

            for page in pages:
                md = page.markdown or ""
                # Get URL from metadata (Pydantic object, use getattr)
                meta = page.metadata
                url = ""
                if meta:
                    url = getattr(meta, 'source_url', '') or getattr(meta, 'url', '') or ""
                if not url or url in seen_urls or len(md) < 100:
                    continue

                seen_urls.add(url)
                title = extract_title_from_markdown(md)
                content = clean_markdown(md)
                category = classify_article(title, content)

                all_articles.append({
                    "title": title[:200] if title else "未命名文章",
                    "url": url,
                    "category": category,
                    "content": content,
                    "source": "kaoyan.com",
                    "scraped_at": datetime.now().isoformat(),
                })

            time.sleep(3)

        except Exception as e:
            logger.error(f"Crawl failed for {target_url}: {e}")
            time.sleep(5)

    return all_articles


def scrape_kaoyan_articles():
    """Scrape individual known article URLs."""
    from firecrawl import FirecrawlApp

    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    articles = []

    # Known article URLs from previous scraping
    urls = [
        "https://www.kaoyan.com/article/1/9370/b1e62fa61d2c467caeffce554046810f",
        "https://www.kaoyan.com/article/1/9370/09823affe8384c3ea46729402ba911ce",
        "https://www.kaoyan.com/article/1/9370/fd76e22c078447d4b0acedd6f88ce5d4",
        "https://www.kaoyan.com/article/1/9370/8b9e6e1c6b6c4f8e9a7d5e3f2a1b0c9d",
    ]

    for url in urls:
        logger.info(f"Scraping individual: {url}")
        try:
            result = app.scrape(url, formats=["markdown"])
            md = getattr(result, 'markdown', '') or ""
            if not md and hasattr(result, 'data'):
                md = result.data.get('markdown', '') if isinstance(result.data, dict) else ""
            if md and len(md) > 100:
                title = extract_title_from_markdown(md)
                content = clean_markdown(md)
                category = classify_article(title, content)
                articles.append({
                    "title": title[:200] if title else "未命名文章",
                    "url": url,
                    "category": category,
                    "content": content,
                    "source": "kaoyan.com",
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(2)
        except Exception as e:
            logger.error(f"Scrape failed for {url}: {e}")
            time.sleep(2)

    return articles


def crawl_yanzhao():
    """Scrape yz.chsi.com.cn for official grad school data."""
    from firecrawl import FirecrawlApp

    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    articles = []

    urls = [
        "https://yz.chsi.com.cn/kyzx/",
        "https://yz.chsi.com.cn/zsml/",
    ]

    for url in urls:
        logger.info(f"Scraping yanzhao: {url}")
        try:
            result = app.scrape(url, formats=["markdown"])
            md = getattr(result, 'markdown', '') or ""
            if md and len(md) > 100:
                title = extract_title_from_markdown(md) or "研招网信息"
                content = clean_markdown(md)
                articles.append({
                    "title": title[:200],
                    "url": url,
                    "category": "政策",
                    "content": content,
                    "source": "yz.chsi.com.cn",
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(2)
        except Exception as e:
            logger.error(f"Scrape failed for {url}: {e}")
            time.sleep(2)

    return articles


def main():
    print("=" * 60)
    print("Firecrawl 批量爬取考研真实数据")
    print(f"API Key: {'已配置' if FIRECRAWL_API_KEY else '未配置'}")
    print("=" * 60)

    all_articles = []
    seen_urls = set()

    # Phase 1: Crawl kaoyan.com (batch)
    print("\n[1/3] 批量爬取 kaoyan.com ...")
    kaoyan_batch = crawl_kaoyan_batch()
    for a in kaoyan_batch:
        if a['url'] not in seen_urls:
            seen_urls.add(a['url'])
            all_articles.append(a)
    print(f"   获得 {len(kaoyan_batch)} 篇 (去重后总计: {len(all_articles)})")

    # Phase 2: Scrape individual articles
    print("\n[2/3] 爬取已知文章页面 ...")
    time.sleep(5)  # Wait for rate limit reset
    individual = scrape_kaoyan_articles()
    for a in individual:
        if a['url'] not in seen_urls:
            seen_urls.add(a['url'])
            all_articles.append(a)
    print(f"   获得 {len(individual)} 篇 (去重后总计: {len(all_articles)})")

    # Phase 3: Scrape yanzhao
    print("\n[3/3] 爬取 yz.chsi.com.cn ...")
    time.sleep(5)
    yanzhao = crawl_yanzhao()
    for a in yanzhao:
        if a['url'] not in seen_urls:
            seen_urls.add(a['url'])
            all_articles.append(a)
    print(f"   获得 {len(yanzhao)} 篇 (去重后总计: {len(all_articles)})")

    # Save
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_articles": len(all_articles),
        "articles": all_articles,
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    categories = {}
    for a in all_articles:
        cat = a.get('category', 'unknown')
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n{'=' * 60}")
    print(f"爬取完成！")
    print(f"  总计: {len(all_articles)} 篇文章")
    print(f"  分类分布: {json.dumps(categories, ensure_ascii=False)}")
    print(f"  保存至: {OUTPUT_FILE}")
    print(f"{'=' * 60}")

    return output


if __name__ == "__main__":
    main()
