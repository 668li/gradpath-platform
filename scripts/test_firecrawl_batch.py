# -*- coding: utf-8 -*-
"""Firecrawl批量爬取真实考研数据"""
import sys, os, json, time
sys.stdout.reconfigure(encoding='utf-8')

os.environ["FIRECRAWL_API_KEY"] = "fc-ec9fa1ce53474816bbbe0865cbfb3700"

from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key=os.environ["FIRECRAWL_API_KEY"])

def scrape_url(url, label=""):
    """用Firecrawl爬取单个URL"""
    try:
        result = app.scrape(url, formats=["markdown"])
        md = result.markdown if hasattr(result, 'markdown') else ""
        print(f"  [{label}] {len(md)} chars")
        return md
    except Exception as e:
        print(f"  [{label}] ERROR: {str(e)[:100]}")
        return ""

def crawl_site(start_url, limit=20):
    """用Firecrawl爬取整个站点"""
    try:
        print(f"Crawling {start_url} (limit={limit})...")
        result = app.crawl(start_url, limit=limit, scrape_options={"formats": ["markdown"]})
        pages = result.data if hasattr(result, 'data') else []
        print(f"  Got {len(pages)} pages")
        return pages
    except Exception as e:
        print(f"  CRAWL ERROR: {str(e)[:200]}")
        return []

# === Test 1: Batch scrape specific pages ===
print("=== Test 1: Batch Scrape ===")
urls = [
    ("kaoyan首页", "https://www.kaoyan.com/"),
    ("研招网首页", "https://yz.chsi.com.cn/"),
    ("考研经验", "https://www.kaoyan.com/experience/"),
    ("调剂经验", "https://www.kaoyan.com/adjust/1/9/list"),
    ("备考策略", "https://www.kaoyan.com/strategy/"),
    ("院校信息", "https://www.kaoyan.com/college"),
    ("新浪考研", "https://edu.sina.com.cn/kaoyan/"),
    ("新东方考研", "https://kaoyan.koolearn.com/"),
]

results = []
for label, url in urls:
    md = scrape_url(url, label)
    results.append({"label": label, "url": url, "content": md})
    time.sleep(1)

# === Test 2: Crawl kaoyan.com site ===
print("\n=== Test 2: Crawl kaoyan.com ===")
crawl_pages = crawl_site("https://www.kaoyan.com/", limit=15)
for page in crawl_pages:
    if hasattr(page, 'metadata') and hasattr(page, 'markdown'):
        url = getattr(page.metadata, 'sourceURL', 'unknown')
        md_len = len(page.markdown) if page.markdown else 0
        print(f"  Crawled: {url[:60]} ({md_len} chars)")

# Save all results
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "firecrawl_data.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump({
        "batch_scrape": results,
        "crawl_results": len(crawl_pages),
        "total_batch_chars": sum(len(r["content"]) for r in results),
    }, f, ensure_ascii=False, indent=2)

print(f"\n=== Summary ===")
print(f"Batch scraped: {len(results)} URLs, {sum(len(r['content']) for r in results)} total chars")
print(f"Crawled: {len(crawl_pages)} pages")
print(f"Saved to: {output_path}")
