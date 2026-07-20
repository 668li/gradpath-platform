# -*- coding: utf-8 -*-
"""Civil service exam scraper — fetches articles from offcn.com and huatu.com.

Uses httpx to scrape public content from:
  - https://www.offcn.com/gwy/ (中公教育国考)
  - https://www.huatu.com/gwy/ (华图教育国考)

Outputs: civil_service_expanded.json
"""
import asyncio
import json
import os
import re
import sys

import httpx

OUTPUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "civil_service_expanded.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# Offcn section URLs mapped to categories
OFFCN_SECTIONS = [
    ("https://www.offcn.com/gwy/", "国考", "offcn"),
    ("https://www.offcn.com/sksy/", "省考", "offcn"),
    ("https://www.offcn.com/xd/", "选调", "offcn"),
    ("https://www.offcn.com/shiyedanwei/", "事业单位", "offcn"),
]

# Huatu section URLs mapped to categories
HUATU_SECTIONS = [
    ("https://www.huatu.com/guojia/", "国考", "huatu"),
    ("https://www.huatu.com/sheng/", "省考", "huatu"),
    ("https://www.huatu.com/xds/", "选调", "huatu"),
    ("https://www.huatu.com/sydw/", "事业单位", "huatu"),
]


def clean_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', '\n', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def extract_links(html: str, base_url: str) -> list[dict]:
    """Extract article links from a listing page HTML.

    Filters out navigation, homepage, partner-site, and non-article links.
    Article links typically contain date patterns (2026/07, 202607) or
    numeric article IDs, and have meaningful titles.
    """
    from urllib.parse import urlparse, urljoin
    base_domain = urlparse(base_url).netloc

    results = []
    patterns = [
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{5,120})</a>',
        r'<a[^>]+>([^<]{5,120})</a>\s*<[^>]+href=["\']([^"\']+)["\']',
    ]

    skip_title = {
        '登录', '注册', '首页', '更多', '>>', '下一页', '上一页', '返回',
        '关于我们', '联系我们', '加入我们', '法律声明', '意见反馈', '客服',
        '设为首页', '收藏本站', '手机版', 'APP下载', '关注我们',
        '地方公务员', '国家公务员', '公务员考试', 'MBA', 'MPA', 'PMP',
    }
    skip_url_sub = {'#', 'javascript:', '.css', '.js', '.png', '.jpg', '.gif', '.ico', '.svg'}

    # Article URL patterns — these indicate real article pages
    article_patterns = [
        r'/\d{4}/\d{2,4}/\d+',  # offcn date path: /2026/0717/34809.html
        r'/\d{4}[-/]\d{2}',     # date in URL: 2026-07 or 2026/07
        r'/\d{6,}\.html',        # numeric article ID: 100034.html
        r'/detail[/?]',          # detail page
        r'/news/',               # news path
        r'/article/',            # generic article path
        r'/p/\d+',               # post ID
    ]

    # Domain patterns to exclude (ads, partner sites, course pages)
    exclude_domain_patterns = ['i.offcn.com', 'ncre.offcn.com', 'mbazl.com', 'm.offcn.com']

    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, html):
            groups = m.groups()
            url, title = groups[0], groups[1]
            if pat == patterns[1]:
                url, title = title, url
            title = title.strip()

            if len(title) < 5:
                continue

            # Skip navigation keywords
            if any(skip in title for skip in skip_title):
                continue

            # Skip utility URLs
            if any(skip in url for skip in skip_url_sub):
                continue

            # Normalize protocol-relative URLs
            if url.startswith('//'):
                url = 'https:' + url

            # Resolve relative URLs
            if not url.startswith('http'):
                url = urljoin(base_url, url)

            parsed = urlparse(url)

            # Skip partner/ad domains
            if any(ed in parsed.netloc for ed in exclude_domain_patterns):
                continue

            # Skip non-matching domains
            if base_domain not in parsed.netloc and parsed.netloc not in base_domain:
                continue

            path = parsed.path.rstrip('/')

            # Skip bare homepage
            if not path or path == '/':
                continue

            if url in seen:
                continue

            # Score: check if URL matches article patterns
            is_article = any(re.search(ap, url) for ap in article_patterns)

            # For offcn.com: skip navigation-only paths
            if 'offcn.com' in parsed.netloc:
                nav_paths = {'/gwy', '/sksy', '/xd', '/shiyedanwei',
                             '/guojia', '/sheng', '/sydw', '/xds',
                             '/gwy/kaoshi', '/gwy/zixun', '/gwy/baokao'}
                if path in nav_paths:
                    continue

            seen.add(url)
            results.append({"title": title, "url": url, "_is_article": is_article})

    # Sort: article-like URLs first, then by title length
    results.sort(key=lambda x: (-int(x.get("_is_article", False)), -len(x["title"])))
    for r in results:
        r.pop("_is_article", None)
    return results


async def fetch_page(client: httpx.AsyncClient, url: str) -> str | None:
    """Fetch a page, return HTML or None on failure."""
    try:
        resp = await client.get(url, follow_redirects=True, timeout=20)
        if resp.status_code == 200:
            return resp.text
        print(f"  [WARN] {url} -> status {resp.status_code}")
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
    return None


async def scrape_offcn(client: httpx.AsyncClient) -> list[dict]:
    """Scrape articles from offcn.com (中公教育)."""
    articles = []
    for url, category, source in OFFCN_SECTIONS:
        print(f"  [offcn] Fetching {url} ({category})...")
        html = await fetch_page(client, url)
        if not html:
            continue
        links = extract_links(html, url)
        print(f"  [offcn] Found {len(links)} links in {category}")

        # Fetch each article's content
        for link in links[:30]:  # cap at 30 per section
            article_html = await fetch_page(client, link["url"])
            if not article_html:
                continue
            # Extract main content from article page
            content = extract_article_content(article_html)
            if len(content) < 30:
                continue
            articles.append({
                "title": link["title"][:200],
                "content": content[:5000],
                "source": source,
                "category": category,
                "url": link["url"],
            })
            await asyncio.sleep(0.5)  # rate limit
    return articles


def extract_article_content(html: str) -> str:
    """Extract meaningful text content from an article page."""
    # Try to find article body div
    body_patterns = [
        r'<div[^>]*class="[^"]*(?:article|content|detail|news)[^"]*"[^>]*>(.*?)</div>',
        r'<div[^>]*id="[^"]*(?:article|content|detail|news)[^"]*"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>',
    ]
    body = ""
    for pat in body_patterns:
        m = re.search(pat, html, re.DOTALL)
        if m:
            body = m.group(1)
            break
    if not body:
        # Fallback: use everything between first <p> and last </p>
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', html, re.DOTALL)
        body = '\n'.join(paragraphs)

    return clean_html(body)


async def scrape_huatu(client: httpx.AsyncClient) -> list[dict]:
    """Scrape articles from huatu.com (华图教育)."""
    articles = []
    for url, category, source in HUATU_SECTIONS:
        print(f"  [huatu] Fetching {url} ({category})...")
        html = await fetch_page(client, url)
        if not html:
            continue
        links = extract_links(html, url)
        print(f"  [huatu] Found {len(links)} links in {category}")

        for link in links[:30]:
            article_html = await fetch_page(client, link["url"])
            if not article_html:
                continue
            content = extract_article_content(article_html)
            if len(content) < 30:
                continue
            articles.append({
                "title": link["title"][:200],
                "content": content[:5000],
                "source": source,
                "category": category,
                "url": link["url"],
            })
            await asyncio.sleep(0.5)
    return articles


def supplement_with_local_data(articles: list[dict]) -> list[dict]:
    """If web scraping yields few results, supplement from local civil_service_data.json."""
    existing_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "civil_service_data.json")
    if not os.path.exists(existing_path):
        return articles

    try:
        with open(existing_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return articles

    existing_urls = {a["url"] for a in articles}
    count = 0
    for source_info in data.get("sources", []):
        source_name = source_info.get("name", "中公教育")
        source_key = "offcn" if "中公" in source_name else "huatu"
        for section in source_info.get("sections", []):
            category = section.get("category", "")
            # Map categories
            cat_map = {
                "国家公务员": "国考", "公务员": "国考",
                "省考": "省考", "选调生": "选调",
                "事业单位": "事业单位", "教师招聘": "事业单位",
                "医疗招聘": "事业单位", "公选遴选": "省考",
                "国企招聘": "事业单位", "教师资格": "事业单位",
                "三支一扶": "事业单位",
            }
            mapped_cat = cat_map.get(category, "国考")
            for item in section.get("items", []):
                # Create synthetic URL for dedup
                fake_url = f"local://{source_key}/{mapped_cat}/{hash(item)}"
                if fake_url in existing_urls:
                    continue
                existing_urls.add(fake_url)
                articles.append({
                    "title": item[:200],
                    "content": f"{item}\n\n来源: {source_name}\n分类: {mapped_cat}",
                    "source": source_key,
                    "category": mapped_cat,
                    "url": fake_url,
                })
                count += 1

    if count > 0:
        print(f"  [supplement] Added {count} items from local civil_service_data.json")
    return articles


async def main():
    print("=" * 60)
    print("Civil Service Exam Scraper (offcn + huatu)")
    print("=" * 60)

    all_articles = []

    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=httpx.Timeout(20),
        follow_redirects=True,
    ) as client:
        # Scrape offcn.com
        print("\n[1/2] Scraping offcn.com (中公教育)...")
        offcn_articles = await scrape_offcn(client)
        print(f"  -> Got {len(offcn_articles)} articles from offcn")
        all_articles.extend(offcn_articles)

        # Scrape huatu.com
        print("\n[2/2] Scraping huatu.com (华图教育)...")
        huatu_articles = await scrape_huatu(client)
        print(f"  -> Got {len(huatu_articles)} articles from huatu")
        all_articles.extend(huatu_articles)

    # Supplement with local data if scraping was sparse
    if len(all_articles) < 50:
        print("\n[Supplement] Web scraping sparse, adding local data...")
        all_articles = supplement_with_local_data(all_articles)

    # Deduplicate by URL
    seen = set()
    unique = []
    for a in all_articles:
        if a["url"] not in seen:
            seen.add(a["url"])
            unique.append(a)

    # Save output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique, f, ensure_ascii=False, indent=2)

    # Stats
    categories = {}
    sources = {}
    for a in unique:
        categories[a["category"]] = categories.get(a["category"], 0) + 1
        sources[a["source"]] = sources.get(a["source"], 0) + 1

    print(f"\n{'=' * 60}")
    print(f"Total articles: {len(unique)}")
    print(f"By category: {categories}")
    print(f"By source: {sources}")
    print(f"Saved to: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
