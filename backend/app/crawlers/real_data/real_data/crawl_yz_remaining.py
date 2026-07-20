# -*- coding: utf-8 -*-
"""
Crawl remaining yz.chsi.com.cn sections using Firecrawl scrape
1. 招生简章 (zsjz)
2. 复试经验 (fstj)
"""
import os
import re
import json
import time
from datetime import datetime
from pathlib import Path

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY

from firecrawl import FirecrawlApp

OUTPUT_FILE = Path(__file__).parent / "yz_round2.json"

SECTIONS = [
    {
        "name": "招生简章",
        "list_url": "https://yz.chsi.com.cn/kyzx/zsjz/",
        "limit": 30,
    },
    {
        "name": "复试经验",
        "list_url": "https://yz.chsi.com.cn/kyzx/fstj/",
        "limit": 30,
    },
]


def extract_links_from_markdown(markdown, base_url):
    """Extract article links from markdown content."""
    links = []
    # Match markdown links: [text](url)
    for match in re.finditer(r'\[([^\]]+)\]\((https?://[^)]+)\)', markdown):
        title, url = match.group(1), match.group(2)
        links.append({"title": title, "url": url})

    # Also match relative links
    for match in re.finditer(r'\[([^\]]+)\]\((/[^)]+)\)', markdown):
        title, rel = match.group(1), match.group(2)
        full_url = f"https://yz.chsi.com.cn{rel}"
        links.append({"title": title, "url": full_url})

    # Also find plain URLs
    for match in re.finditer(r'(https?://yz\.chsi\.com\.cn/[^\s\)\"]+)', markdown):
        url = match.group(1)
        if url not in [l["url"] for l in links]:
            links.append({"title": "", "url": url})

    return links


def scrape_with_retry(app, url, retries=3):
    """Scrape a URL with retries."""
    for attempt in range(retries):
        try:
            result = app.scrape(
                url,
                formats=["markdown"],
                only_main_content=True,
                timeout=30000,
            )
            return result
        except Exception as e:
            err_str = str(e)
            if "Payment Required" in err_str or "Insufficient credits" in err_str:
                print(f"  [!] Out of credits on attempt {attempt+1}")
                return None
            print(f"  [!] Attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None


def crawl_section(app, section_info):
    """Crawl a section: get list page, extract links, scrape articles."""
    name = section_info["name"]
    list_url = section_info["list_url"]
    limit = section_info["limit"]

    print(f"\n{'='*60}")
    print(f"Section: {name}")
    print(f"List URL: {list_url}")
    print(f"{'='*60}")

    # Step 1: Scrape the list/index page
    print(f"\n[1/3] Scraping list page...")
    result = scrape_with_retry(app, list_url)
    if not result:
        print(f"  Failed to scrape list page for {name}")
        return [], 0, 0

    markdown = getattr(result, 'markdown', '') or ''
    if not markdown and isinstance(result, dict):
        markdown = result.get('markdown', '')

    print(f"  List page markdown: {len(markdown)} chars")

    # Step 2: Extract article links
    print(f"\n[2/3] Extracting article links...")
    links = extract_links_from_markdown(markdown, list_url)

    # Deduplicate
    seen_urls = set()
    unique_links = []
    for link in links:
        if link["url"] not in seen_urls:
            seen_urls.add(link["url"])
            unique_links.append(link)

    # Only keep yz.chsi.com.cn links that look like articles
    article_links = [
        l for l in unique_links
        if "chsi.com.cn" in l["url"] and l["url"] != list_url
    ]

    print(f"  Found {len(article_links)} unique article links")
    article_links = article_links[:limit]
    print(f"  Will scrape {len(article_links)} articles (limit={limit})")

    # Step 3: Scrape each article
    print(f"\n[3/3] Scraping articles...")
    all_data = []

    # Include the list page itself as the first entry
    list_entry = {
        "source": name,
        "url": list_url,
        "title": f"{name} - 目录页",
        "markdown": markdown,
        "chars": len(markdown),
    }
    all_data.append(list_entry)

    for i, link in enumerate(article_links):
        print(f"  [{i+1}/{len(article_links)}] {link['title'][:50] or link['url'][:60]}...")

        art_result = scrape_with_retry(app, link["url"], retries=2)
        if not art_result:
            print(f"    Skipped (no result)")
            continue

        art_md = getattr(art_result, 'markdown', '') or ''
        if not art_md and isinstance(art_result, dict):
            art_md = art_result.get('markdown', '')

        art_title = link["title"]
        if not art_title and isinstance(art_result, dict):
            meta = art_result.get('metadata', {})
            art_title = meta.get('title', '') if isinstance(meta, dict) else ''

        entry = {
            "source": name,
            "url": link["url"],
            "title": art_title,
            "markdown": art_md,
            "chars": len(art_md),
        }
        all_data.append(entry)

        # Rate limit
        time.sleep(1)

    total_chars = sum(d["chars"] for d in all_data)
    page_count = len(all_data)
    print(f"\n  {name}: {page_count} pages, {total_chars:,} chars")

    return all_data, page_count, total_chars


def main():
    print("=" * 60)
    print("yz.chsi.com.cn Remaining Sections Crawler (Firecrawl Scrape)")
    print("=" * 60)

    app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

    all_data = {
        "timestamp": datetime.now().isoformat(),
        "sections": {},
        "summary": {
            "total_pages": 0,
            "total_chars": 0,
        },
    }

    for section_info in SECTIONS:
        name = section_info["name"]
        pages, count, chars = crawl_section(app, section_info)

        all_data["sections"][name] = {
            "url": section_info["list_url"],
            "pages": pages,
            "page_count": count,
            "total_chars": chars,
        }

        all_data["summary"]["total_pages"] += count
        all_data["summary"]["total_chars"] += chars

        time.sleep(2)

    # Save
    OUTPUT_FILE.write_text(
        json.dumps(all_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)
    print(f"Total pages crawled: {all_data['summary']['total_pages']}")
    print(f"Total chars: {all_data['summary']['total_chars']:,}")
    print(f"\nBreakdown:")
    for section, data in all_data["sections"].items():
        print(f"  {section}: {data['page_count']} pages, {data['total_chars']:,} chars")
    print(f"\nSaved to: {OUTPUT_FILE}")

    return all_data["summary"]


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    main()
