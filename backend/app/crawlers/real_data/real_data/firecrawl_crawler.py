# -*- coding: utf-8 -*-
"""Firecrawl-based crawler for real graduate school data.

Scrapes real data from:
1. 研招网 (yz.chsi.com.cn) - scoreline data, program info
2. 考研帮 (kaoyan.com) - experience posts, community data

Requires FIRECRAWL_API_KEY env var. Falls back to httpx if not set.

Usage:
    python -m app.crawlers.real_data.firecrawl_crawler
    python -m app.crawlers.real_data.firecrawl_crawler --source yanzhao
    python -m app.crawlers.real_data.firecrawl_crawler --source kaoyan
"""
import os
import sys
import json
import re
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Output path
OUTPUT_DIR = Path(__file__).parent
OUTPUT_FILE = OUTPUT_DIR / "scraped_data.json"

# ─── Firecrawl imports ───────────────────────────────────────────
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

def _get_firecrawl_client():
    """Return Firecrawl client or None if not configured."""
    if not FIRECRAWL_API_KEY:
        logger.warning("FIRECRAWL_API_KEY not set — will use httpx fallback")
        return None
    try:
        from firecrawl import FirecrawlApp
        return FirecrawlApp(api_key=FIRECRAWL_API_KEY)
    except ImportError:
        logger.warning("firecrawl-py not installed — using httpx fallback")
        return None


# ─── Data sources ────────────────────────────────────────────────

YANZHAO_URLS = [
    "https://yz.chsi.com.cn/zsml/queryAction.do",
    "https://yz.chsi.com.cn/kyzx/",
]

KAOYAN_URLS = [
    "https://www.kaoyan.com/",
    "https://www.kaoyan.com/zhao/",
]

# ─── HTTP fallback ───────────────────────────────────────────────

def _httpx_scrape(url: str, timeout: int = 30) -> Optional[str]:
    """Fallback scraper using httpx."""
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.error(f"httpx scrape failed for {url}: {e}")
        return None


def _firecrawl_scrape(url: str, params: dict = None) -> Optional[dict]:
    """Scrape using Firecrawl API."""
    client = _get_firecrawl_client()
    if not client:
        return None
    try:
        result = client.scrape_url(url, params=params or {
            "formats": ["markdown", "html"],
            "timeout": 30000,
        })
        return result
    except Exception as e:
        logger.error(f"Firecrawl scrape failed for {url}: {e}")
        return None


# ─── Parse functions ─────────────────────────────────────────────

def _parse_yanzhao_html(html: str) -> list[dict]:
    """Parse yanzhao.com.cn HTML for program data."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    programs = []

    # Look for program listing tables
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # skip header
            cells = row.find_all(["td", "th"])
            if len(cells) >= 3:
                text = [c.get_text(strip=True) for c in cells]
                programs.append({
                    "university": text[0] if text else "",
                    "major": text[1] if len(text) > 1 else "",
                    "department": text[2] if len(text) > 2 else "",
                    "raw_cells": text,
                })

    # Also look for div-based listings
    items = soup.find_all("div", class_=re.compile(r"item|result|list"))
    for item in items[:50]:
        title_el = item.find(["h3", "h4", "a", "span"])
        if title_el:
            title = title_el.get_text(strip=True)
            programs.append({
                "title": title,
                "source": "yanzhao_div",
            })

    return programs


def _parse_kaoyan_html(html: str) -> list[dict]:
    """Parse kaoyan.com HTML for experience posts."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    posts = []

    # Look for post/article items
    items = soup.find_all(["div", "li"], class_=re.compile(r"item|post|article|thread"))
    for item in items[:100]:
        title_el = item.find(["h2", "h3", "h4", "a"])
        if title_el:
            title = title_el.get_text(strip=True)
            link = ""
            if title_el.name == "a":
                link = title_el.get("href", "")
            else:
                link_el = item.find("a")
                if link_el:
                    link = link_el.get("href", "")

            desc_el = item.find(["p", "span", "div"], class_=re.compile(r"desc|summary|content"))
            desc = desc_el.get_text(strip=True) if desc_el else ""

            posts.append({
                "title": title,
                "link": link,
                "description": desc,
                "source": "kaoyan",
            })

    return posts


def _parse_markdown_content(content: str, source: str) -> list[dict]:
    """Parse markdown content from Firecrawl into structured data."""
    items = []
    lines = content.split("\n")
    current_item = {}

    for line in lines:
        line = line.strip()
        if not line:
            if current_item:
                items.append(current_item)
                current_item = {}
            continue

        # Detect headers as item separators
        if line.startswith("# ") or line.startswith("## "):
            if current_item:
                items.append(current_item)
            current_item = {"title": line.lstrip("# ").strip(), "source": source}
        elif current_item:
            current_item.setdefault("content_lines", []).append(line)

    if current_item:
        items.append(current_item)

    return items


# ─── Scraping pipeline ───────────────────────────────────────────

def scrape_yanzhao(client=None) -> list[dict]:
    """Scrape yanzhao.com.cn for program and scoreline data."""
    all_data = []

    for url in YANZHAO_URLS:
        logger.info(f"Scraping yanzhao: {url}")

        if client:
            result = _firecrawl_scrape(url)
            if result:
                md = result.get("markdown", "")
                html = result.get("html", "")
                if md:
                    all_data.extend(_parse_markdown_content(md, "yanzhao"))
                if html:
                    all_data.extend(_parse_yanzhao_html(html))
        else:
            html = _httpx_scrape(url)
            if html:
                all_data.extend(_parse_yanzhao_html(html))

        time.sleep(2)  # rate limit

    return all_data


def scrape_kaoyan(client=None) -> list[dict]:
    """Scrape kaoyan.com for experience posts."""
    all_data = []

    for url in KAOYAN_URLS:
        logger.info(f"Scraping kaoyan: {url}")

        if client:
            result = _firecrawl_scrape(url)
            if result:
                md = result.get("markdown", "")
                html = result.get("html", "")
                if md:
                    all_data.extend(_parse_markdown_content(md, "kaoyan"))
                if html:
                    all_data.extend(_parse_kaoyan_html(html))
        else:
            html = _httpx_scrape(url)
            if html:
                all_data.extend(_parse_kaoyan_html(html))

        time.sleep(2)  # rate limit

    return all_data


# ─── Main entry point ────────────────────────────────────────────

def run_crawler(source: str = "all") -> dict:
    """Run the Firecrawl crawler and save results."""
    client = _get_firecrawl_client()
    results = {
        "timestamp": datetime.now().isoformat(),
        "source": source,
        "firecrawl_available": client is not None,
        "data": {},
    }

    if source in ("all", "yanzhao"):
        yanzhao_data = scrape_yanzhao(client)
        results["data"]["yanzhao"] = yanzhao_data
        logger.info(f"Yanzhao: scraped {len(yanzhao_data)} items")

    if source in ("all", "kaoyan"):
        kaoyan_data = scrape_kaoyan(client)
        results["data"]["kaoyan"] = kaoyan_data
        logger.info(f"Kaoyan: scraped {len(kaoyan_data)} items")

    # Save to file
    OUTPUT_FILE.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Results saved to {OUTPUT_FILE}")

    # Summary
    total = sum(len(v) for v in results["data"].values())
    return {
        "status": "success" if total > 0 else "empty",
        "total_items": total,
        "output_file": str(OUTPUT_FILE),
        "firecrawl_used": client is not None,
        "breakdown": {k: len(v) for k, v in results["data"].items()},
    }


# ─── CLI ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Firecrawl real data crawler")
    parser.add_argument("--source", choices=["all", "yanzhao", "kaoyan"], default="all",
                        help="Data source to scrape")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    print(f"Firecrawl API key: {'SET' if FIRECRAWL_API_KEY else 'NOT SET (using httpx fallback)'}")
    result = run_crawler(args.source)
    print(json.dumps(result, ensure_ascii=False, indent=2))
