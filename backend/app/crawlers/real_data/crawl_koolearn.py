# -*- coding: utf-8 -*-
"""Crawl 新东方考研 and 考研学长学姐经验 using httpx (Firecrawl credits exhausted)."""
import os
import json
import re
import time
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_FILE = Path(__file__).parent / "koolearn_crawled.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


def fetch_page(client: httpx.Client, url: str) -> Optional[str]:
    """Fetch a single page, return HTML or None."""
    try:
        resp = client.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch {url}: {e}")
        return None


def extract_article_links(html: str, base_url: str) -> list[dict]:
    """Extract article links from a listing page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()

    # Find all <a> tags with href
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        title = a.get_text(strip=True)

        # Filter: skip anchors, javascript, images, too-short titles
        if not title or len(title) < 4:
            continue
        if full_url in seen:
            continue
        if any(x in href for x in ["javascript:", "#", "mailto:", ".jpg", ".png", ".gif", ".css", ".js"]):
            continue

        seen.add(full_url)
        links.append({"url": full_url, "title": title})

    return links


def extract_article_content(html: str) -> dict:
    """Extract article content from a detail page."""
    soup = BeautifulSoup(html, "html.parser")

    title = ""
    # Try common title selectors
    for sel in ["h1", "h2.title", ".article-title", ".post-title", ".content-title"]:
        el = soup.select_one(sel)
        if el:
            title = el.get_text(strip=True)
            break

    content_parts = []
    # Try common content selectors
    for sel in [".article-content", ".post-content", ".content", ".entry-content", "article", ".detail-content", "#content", ".main-content", ".news-content"]:
        els = soup.select(sel)
        for el in els:
            text = el.get_text(separator="\n", strip=True)
            if text and len(text) > 50:
                content_parts.append(text)

    if not content_parts:
        # Fallback: get body text
        body = soup.find("body")
        if body:
            # Remove scripts and styles
            for tag in body.find_all(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            content_parts.append(body.get_text(separator="\n", strip=True))

    content = "\n\n".join(content_parts)

    # Extract metadata
    meta = {}
    for tag in soup.find_all("meta"):
        name = tag.get("name", tag.get("property", ""))
        content_val = tag.get("content", "")
        if name and content_val:
            meta[name] = content_val

    return {
        "title": title,
        "content": content[:8000],  # limit content size
        "meta": meta,
    }


def crawl_koolearn(limit: int = 30) -> list[dict]:
    """Crawl 新东方考研 kaoyan.koolearn.com."""
    results = []
    base_url = "https://kaoyan.koolearn.com/"

    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        # Fetch main page
        html = fetch_page(client, base_url)
        if not html:
            logger.error("Failed to fetch koolearn main page")
            return results

        # Extract links
        links = extract_article_links(html, base_url)
        logger.info(f"Found {len(links)} links on koolearn")

        # Filter for article-like links (考研 related)
        article_links = []
        for link in links:
            url = link["url"]
            title = link["title"]
            # Keep links that look like articles (contain /news/, /zx/, article patterns, or long enough)
            if any(kw in url for kw in ["news", "zx", "kaoyan", "article", "post", "jy", "info", "detail"]) or len(title) > 8:
                article_links.append(link)

        # If not enough filtered links, use all
        if len(article_links) < limit:
            article_links = links

        logger.info(f"Crawling {min(limit, len(article_links))} pages from koolearn")

        for link in article_links[:limit]:
            url = link["url"]
            logger.info(f"  Fetching: {url}")
            page_html = fetch_page(client, url)
            if page_html:
                content = extract_article_content(page_html)
                results.append({
                    "source": "新东方考研",
                    "url": url,
                    "title": content["title"] or link["title"],
                    "markdown": content["content"],
                })
            time.sleep(1)

    return results


def crawl_kaoyan_senior(limit: int = 20) -> list[dict]:
    """Crawl 考研学长学姐经验 kaoyan.com/senior/."""
    results = []
    base_url = "https://www.kaoyan.com/senior/"

    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        html = fetch_page(client, base_url)
        if not html:
            logger.error("Failed to fetch kaoyan senior page")
            return results

        links = extract_article_links(html, base_url)
        logger.info(f"Found {len(links)} links on kaoyan/senior")

        article_links = [l for l in links if len(l["title"]) > 6]
        if len(article_links) < limit:
            article_links = links

        logger.info(f"Crawling {min(limit, len(article_links))} pages from kaoyan/senior")

        for link in article_links[:limit]:
            url = link["url"]
            logger.info(f"  Fetching: {url}")
            page_html = fetch_page(client, url)
            if page_html:
                content = extract_article_content(page_html)
                results.append({
                    "source": "学长学姐经验",
                    "url": url,
                    "title": content["title"] or link["title"],
                    "markdown": content["content"],
                })
            time.sleep(1)

    return results


def crawl():
    all_results = []
    total_chars = 0

    # 1. 新东方考研
    print("\n=== Crawling 新东方考研 (limit=30) ===")
    koolearn_data = crawl_koolearn(limit=30)
    all_results.extend(koolearn_data)
    total_chars += sum(len(r["markdown"]) for r in koolearn_data)
    print(f"  Got {len(koolearn_data)} pages")

    time.sleep(2)

    # 2. 学长学姐经验
    print("\n=== Crawling 学长学姐经验 (limit=20) ===")
    senior_data = crawl_kaoyan_senior(limit=20)
    all_results.extend(senior_data)
    total_chars += sum(len(r["markdown"]) for r in senior_data)
    print(f"  Got {len(senior_data)} pages")

    output = {
        "timestamp": datetime.now().isoformat(),
        "pages_crawled": len(all_results),
        "total_chars": total_chars,
        "method": "httpx (Firecrawl credits exhausted)",
        "data": all_results,
    }

    OUTPUT_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved to {OUTPUT_FILE}")
    print(f"Pages crawled: {len(all_results)}")
    print(f"Total chars: {total_chars}")
    return output


if __name__ == "__main__":
    crawl()
