# -*- coding: utf-8 -*-
"""Batch scraper for yz.chsi.com.cn sections using direct HTTP."""
import os
import sys
import json
import time
import logging
import re
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://yz.chsi.com.cn"
SECTIONS = {
    "kydt": {"path": "/kyzx/kydt/", "pages": 50, "name": "考研动态"},
    "jybzc": {"path": "/kyzx/jybzc/", "pages": 20, "name": "教育部政策"},
    "zsjz": {"path": "/kyzx/zsjz/", "pages": 30, "name": "招生简章"},
    "fstj": {"path": "/kyzx/fstj/", "pages": 20, "name": "复试经验"},
}

OUTPUT_FILE = Path(__file__).parent / "yz_loop.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_page(url: str) -> str | None:
    import httpx
    try:
        with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return None


def extract_items_from_html(html: str, section_key: str) -> list[dict]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    items = []

    # Try to find article list items
    for li in soup.find_all("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a["href"]
        if not title or len(title) < 4:
            continue
        # Filter for relevant links
        if any(seg in href for seg in ["/kyzx/", "/kydt/", "/jybzc/", "/zsjz/", "/fstj/", "/info/"]):
            full_url = href if href.startswith("http") else BASE_URL + href
            # Try to find date
            date_span = li.find("span", class_=re.compile(r"date|time|pub"))
            date_text = date_span.get_text(strip=True) if date_span else ""
            items.append({
                "title": title,
                "url": full_url,
                "date": date_text,
                "section": section_key,
                "source": "yz.chsi.com.cn",
            })

    # Also check div-based listings
    for div in soup.find_all("div", class_=re.compile(r"list|item|news")):
        a = div.find("a", href=True)
        if not a:
            continue
        title = a.get_text(strip=True)
        href = a["href"]
        if not title or len(title) < 4:
            continue
        if any(seg in href for seg in ["/kyzx/", "/kydt/", "/jybzc/", "/zsjz/", "/fstj/", "/info/"]):
            full_url = href if href.startswith("http") else BASE_URL + href
            items.append({
                "title": title,
                "url": full_url,
                "section": section_key,
                "source": "yz.chsi.com.cn",
            })

    # Fallback: find all links with /info/ pattern (article detail pages)
    if not items:
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True)
            if not title or len(title) < 6:
                continue
            if "/info/" in href or ("kyzx" in href and href.endswith(".html") and "index_" not in href):
                full_url = href if href.startswith("http") else BASE_URL + href
                items.append({
                    "title": title,
                    "url": full_url,
                    "section": section_key,
                    "source": "yz.chsi.com.cn",
                })

    return items


def scrape_section(key: str, config: dict) -> list[dict]:
    path = config["path"]
    max_pages = config["pages"]
    name = config["name"]
    all_items = []
    seen_urls = set()

    logger.info(f"=== Scraping {name} ({path}) - {max_pages} pages ===")

    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"{BASE_URL}{path}"
        else:
            url = f"{BASE_URL}{path}index_{page}.html"

        logger.info(f"[{name}] Page {page}/{max_pages}: {url}")
        html = fetch_page(url)
        if html:
            items = extract_items_from_html(html, key)
            for it in items:
                u = it.get("url", "")
                if u and u not in seen_urls:
                    seen_urls.add(u)
                    all_items.append(it)
            logger.info(f"[{name}] Page {page}: found {len(items)} items (total: {len(all_items)})")
        else:
            logger.warning(f"[{name}] Page {page}: fetch failed")

        time.sleep(1.0)

    logger.info(f"[{name}] Done: {len(all_items)} items")
    return all_items


def main():
    results = {}
    total_pages = 0
    total_chars = 0

    # Scrape homepage first
    logger.info("=== Scraping homepage ===")
    home_html = fetch_page(BASE_URL)
    home_links = []
    if home_html:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(home_html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "yz.chsi.com.cn" in href or href.startswith("/"):
                full = href if href.startswith("http") else BASE_URL + href
                home_links.append(full)
        home_links = list(set(home_links))
        total_chars += len(home_html)
        logger.info(f"Homepage: {len(home_links)} internal links found")
    time.sleep(1.0)

    # Scrape each section
    for key, config in SECTIONS.items():
        items = scrape_section(key, config)
        results[key] = {
            "name": config["name"],
            "items": items,
            "count": len(items),
        }
        total_pages += config["pages"]
        for it in items:
            total_chars += len(json.dumps(it, ensure_ascii=False))

    # Save output
    output = {
        "timestamp": datetime.now().isoformat(),
        "base_url": BASE_URL,
        "homepage_links": home_links,
        "sections": results,
        "stats": {
            "total_pages": total_pages,
            "total_items": sum(s["count"] for s in results.values()),
            "total_chars": total_chars,
        },
    }
    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Saved to {OUTPUT_FILE}")

    print(f"\n=== Done ===")
    print(f"Pages scraped: {total_pages}")
    print(f"Total items: {sum(s['count'] for s in results.values())}")
    print(f"Total chars: {total_chars:,}")


if __name__ == "__main__":
    main()
