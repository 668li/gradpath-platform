# -*- coding: utf-8 -*-
"""Phase 1: Crawl kaoyan.com to discover article URLs."""
import os
import json
import re
import time
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
OUTPUT_DIR = Path(__file__).parent
URLS_FILE = OUTPUT_DIR / "discovered_urls.json"


def main():
    from firecrawl import FirecrawlApp
    app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

    all_urls = set()

    # Crawl main page and sub-pages to discover article links
    targets = [
        "https://www.kaoyan.com/",
        "https://www.kaoyan.com/zhao/",
        "https://www.kaoyan.com/kyzx/",
    ]

    for target_url in targets:
        logger.info(f"Crawling: {target_url}")
        try:
            result = app.crawl(
                target_url,
                limit=30,
                scrape_options={"formats": ["markdown"]},
            )

            if not hasattr(result, 'data') or not result.data:
                logger.warning(f"  No data from {target_url}")
                time.sleep(5)
                continue

            pages = result.data
            logger.info(f"  Got {len(pages)} pages")

            for page in pages:
                md = page.markdown or ""
                meta = page.metadata
                url = ""
                if meta:
                    url = getattr(meta, 'source_url', '') or getattr(meta, 'url', '') or ""

                # Extract article links from markdown
                article_links = re.findall(
                    r'https://www\.kaoyan\.com/article/\d+/\d+/[a-f0-9]+',
                    md
                )
                for link in article_links:
                    # Remove query params
                    link = link.split('?')[0]
                    all_urls.add(link)

                # Also check if current page is an article
                if url and '/article/' in url:
                    url = url.split('?')[0]
                    all_urls.add(url)

            time.sleep(5)

        except Exception as e:
            logger.error(f"Crawl failed for {target_url}: {e}")
            time.sleep(5)

    # Save discovered URLs
    urls_list = sorted(all_urls)
    with open(URLS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"total": len(urls_list), "urls": urls_list}, f, ensure_ascii=False, indent=2)

    print(f"\nDiscovered {len(urls_list)} article URLs")
    print(f"Saved to: {URLS_FILE}")

    # Show first 10
    for u in urls_list[:10]:
        print(f"  {u}")

    return urls_list


if __name__ == "__main__":
    main()
