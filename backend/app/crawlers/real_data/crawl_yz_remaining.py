# -*- coding: utf-8 -*-
"""
Crawl remaining yz.chsi.com.cn sections using httpx + BeautifulSoup
Firecrawl credits exhausted — falls back to direct HTTP scraping.

1. 招生简章 (zsjz)
2. 复试经验 (fstj)
"""
import re
import json
import time
import httpx
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

OUTPUT_FILE = Path(__file__).parent / "yz_round2.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

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


def fetch_page(client, url):
    """Fetch a page and return text content."""
    try:
        resp = client.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        # Try to detect encoding from content-type header or default to utf-8
        content_type = resp.headers.get("content-type", "")
        if "charset=" in content_type:
            encoding = content_type.split("charset=")[-1].strip()
        else:
            encoding = "utf-8"
        try:
            return resp.content.decode(encoding, errors="replace")
        except (UnicodeDecodeError, LookupError):
            return resp.content.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    Error fetching {url}: {e}")
        return None


def extract_article_links(html, base_url, list_url):
    """Extract article links from list page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = []

    # yz.chsi.com.cn typically uses <li> or <div> with <a> tags for article listings
    # Try common patterns

    # Pattern 1: look for list items with links
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        title = a_tag.get_text(strip=True)

        # Skip empty titles, navigation links, etc.
        if not title or len(title) < 4:
            continue

        # Resolve relative URLs
        if href.startswith("/"):
            full_url = f"https://yz.chsi.com.cn{href}"
        elif href.startswith("http"):
            full_url = href
        else:
            continue

        # Only keep article-like links (with ky/ or kyzx/ path patterns)
        if full_url == list_url:
            continue
        if "chsi.com.cn" not in full_url:
            continue
        # Filter for actual article links (usually contain numeric IDs or specific patterns)
        if re.search(r'/kyzx/\w+/\d+', full_url) or re.search(r'/ky/\d+', full_url):
            links.append({"title": title, "url": full_url})

    # Deduplicate by URL
    seen = set()
    unique = []
    for l in links:
        if l["url"] not in seen:
            seen.add(l["url"])
            unique.append(l)

    return unique


def extract_article_content(html, url):
    """Extract article content from a detail page."""
    soup = BeautifulSoup(html, "html.parser")

    # Try to find main content area
    content_el = (
        soup.find("div", class_=re.compile(r"article|content|detail|body|post"))
        or soup.find("div", id=re.compile(r"article|content|detail|body"))
        or soup.find("article")
    )

    if content_el:
        text = content_el.get_text(separator="\n", strip=True)
    else:
        # Fallback: get all text from body
        body = soup.find("body")
        text = body.get_text(separator="\n", strip=True) if body else soup.get_text(separator="\n", strip=True)

    # Extract title
    title_el = soup.find("h1") or soup.find("h2") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""

    return {
        "title": title,
        "content": text,
        "url": url,
    }


def crawl_section(client, section_info):
    """Crawl a section: fetch list page, extract links, scrape articles."""
    name = section_info["name"]
    list_url = section_info["list_url"]
    limit = section_info["limit"]

    print(f"\n{'='*60}")
    print(f"Section: {name}")
    print(f"List URL: {list_url}")
    print(f"{'='*60}")

    # Step 1: Fetch list page
    print(f"\n[1/3] Fetching list page...")
    html = fetch_page(client, list_url)
    if not html:
        print(f"  Failed to fetch list page")
        return [], 0, 0

    print(f"  List page: {len(html)} chars")

    # Step 2: Extract article links
    print(f"\n[2/3] Extracting article links...")
    links = extract_article_links(html, list_url, list_url)
    print(f"  Found {len(links)} article links")
    links = links[:limit]
    print(f"  Will scrape {len(links)} articles (limit={limit})")

    # Step 3: Scrape each article
    print(f"\n[3/3] Scraping articles...")
    all_data = []

    # Include list page content
    soup = BeautifulSoup(html, "html.parser")
    list_text = soup.get_text(separator="\n", strip=True)
    all_data.append({
        "source": name,
        "url": list_url,
        "title": f"{name} - 目录页",
        "markdown": list_text,
        "chars": len(list_text),
    })

    for i, link in enumerate(links):
        print(f"  [{i+1}/{len(links)}] {link['title'][:50]}...")

        art_html = fetch_page(client, link["url"])
        if not art_html:
            print(f"    Skipped (fetch failed)")
            continue

        article = extract_article_content(art_html, link["url"])
        entry = {
            "source": name,
            "url": link["url"],
            "title": article.get("title", link["title"]),
            "markdown": article.get("content", ""),
            "chars": len(article.get("content", "")),
        }
        all_data.append(entry)
        print(f"    OK: {entry['chars']} chars")

        time.sleep(0.5)  # polite delay

    total_chars = sum(d["chars"] for d in all_data)
    page_count = len(all_data)
    print(f"\n  {name}: {page_count} pages, {total_chars:,} chars")

    return all_data, page_count, total_chars


def main():
    print("=" * 60)
    print("yz.chsi.com.cn Remaining Sections Crawler (httpx)")
    print("Firecrawl credits exhausted — using direct HTTP scraping")
    print("=" * 60)

    all_data = {
        "timestamp": datetime.now().isoformat(),
        "method": "httpx+bs4",
        "note": "Firecrawl credits exhausted, used direct HTTP scraping",
        "sections": {},
        "summary": {
            "total_pages": 0,
            "total_chars": 0,
        },
    }

    with httpx.Client(headers=HEADERS, timeout=30, follow_redirects=True) as client:
        for section_info in SECTIONS:
            name = section_info["name"]
            pages, count, chars = crawl_section(client, section_info)

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
    main()
