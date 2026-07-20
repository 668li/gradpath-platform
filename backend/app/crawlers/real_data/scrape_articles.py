# -*- coding: utf-8 -*-
"""Phase 2: Scrape individual article pages discovered in Phase 1.

Reads discovered_urls.json, scrapes each article, saves to firecrawl_scraped.json.

Usage:
    python -m app.crawlers.real_data.scrape_articles
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
URLS_FILE = OUTPUT_DIR / "discovered_urls.json"
OUTPUT_FILE = OUTPUT_DIR / "firecrawl_scraped.json"

CATEGORY_KEYWORDS = {
    "初试": ["初试", "笔试", "政治", "英语一", "数学一", "专业课", "真题"],
    "复试": ["复试", "面试", "英语口语"],
    "调剂": ["调剂"],
    "择校": ["择校", "选学校", "院校", "报考", "目标院校"],
    "备考": ["备考", "复习计划", "时间安排", "学习方法", "复习方法"],
    "政策": ["政策", "招生简章", "考试大纲", "报名"],
    "分数线": ["分数线", "国家线", "复试线", "录取线"],
    "专业分析": ["专业分析", "专业前景", "就业方向", "跨考"],
    "经验分享": ["经验", "心得", "感悟", "上岸"],
}


def clean_markdown(content: str) -> str:
    """Remove CSS noise and clean markdown."""
    if not content:
        return ""
    text = re.sub(r'\{[^}]*\}', '', content)
    text = re.sub(r'/\*!.*?\*/', '', text)
    text = re.sub(r'--tw-[^:]+:[^;]+;', '', text)
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
    """Classify article category."""
    text = (title + " " + content[:2000]).lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return cat
    return "经验分享"


def extract_title(md: str) -> str:
    """Extract title from markdown."""
    for line in md.split('\n'):
        stripped = line.strip()
        if stripped.startswith('# ') or stripped.startswith('## '):
            t = stripped.lstrip('# ').strip()
            if len(t) > 4 and not t.startswith('{') and not t.startswith('!'):
                return t[:200]
    # Try to find title from link text
    for line in md.split('\n'):
        m = re.search(r'\[([^\]]{10,})\]\(https://www\.kaoyan\.com/article/', line)
        if m:
            return m.group(1)[:200]
    return ""


def main():
    print("=" * 60)
    print("Phase 2: Scrape individual articles")
    print("=" * 60)

    # Load discovered URLs
    if not URLS_FILE.exists():
        print(f"ERROR: {URLS_FILE} not found. Run discover_urls.py first.")
        sys.exit(1)

    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        url_data = json.load(f)

    urls = url_data['urls']
    print(f"\nLoaded {len(urls)} URLs to scrape")

    from firecrawl import FirecrawlApp
    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

    articles = []
    errors = 0
    batch_size = 10  # Firecrawl free tier: ~3 req/min

    for i, url in enumerate(urls):
        logger.info(f"[{i+1}/{len(urls)}] Scraping: {url}")
        try:
            result = app.scrape(url, formats=["markdown"])
            md = getattr(result, 'markdown', '') or ""

            if not md or len(md) < 100:
                logger.warning(f"  Empty/short content, skipping")
                errors += 1
                continue

            title = extract_title(md)
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

            logger.info(f"  OK: {title[:50]} ({len(content)} chars)")

        except Exception as e:
            logger.error(f"  FAILED: {e}")
            errors += 1

        # Rate limiting: wait between batches
        if (i + 1) % batch_size == 0:
            logger.info(f"  Rate limit pause after {i+1} requests...")
            time.sleep(10)
        else:
            time.sleep(2)

    # Also scrape yanzhao
    print(f"\nScraping yanzhao...")
    yanzhao_urls = [
        "https://yz.chsi.com.cn/kyzx/",
        "https://yz.chsi.com.cn/zsml/",
    ]
    for url in yanzhao_urls:
        try:
            result = app.scrape(url, formats=["markdown"])
            md = getattr(result, 'markdown', '') or ""
            if md and len(md) > 100:
                title = extract_title(md) or "研招网信息"
                content = clean_markdown(md)
                articles.append({
                    "title": title[:200],
                    "url": url,
                    "category": "政策",
                    "content": content,
                    "source": "yz.chsi.com.cn",
                    "scraped_at": datetime.now().isoformat(),
                })
            time.sleep(3)
        except Exception as e:
            logger.error(f"Yanzhao failed: {e}")

    # Save
    output = {
        "timestamp": datetime.now().isoformat(),
        "total_articles": len(articles),
        "errors": errors,
        "articles": articles,
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    # Summary
    cats = {}
    titled = 0
    for a in articles:
        cat = a.get('category', '?')
        cats[cat] = cats.get(cat, 0) + 1
        if a['title'] != '未命名文章':
            titled += 1

    print(f"\n{'=' * 60}")
    print(f"Scraping complete!")
    print(f"  Total: {len(articles)} articles")
    print(f"  Titled: {titled}")
    print(f"  Errors: {errors}")
    print(f"  Categories: {json.dumps(cats, ensure_ascii=False)}")
    print(f"  Saved to: {OUTPUT_FILE}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
