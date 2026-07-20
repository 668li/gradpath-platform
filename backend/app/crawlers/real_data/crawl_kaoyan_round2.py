import os, json, time

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

urls = [
    ("https://www.kaoyan.com/experience/", "experience"),
    ("https://www.kaoyan.com/news/list/1/9370", "news"),
    ("https://www.kaoyan.com/news/list/1/3946", "wiki"),
]

all_pages = []
total_pages_crawled = 0

for url, category in urls:
    print(f"\n{'='*60}")
    print(f"Crawling {category}: {url} (limit=30)")
    print(f"{'='*60}")
    
    try:
        result = app.crawl(
            url,
            limit=30,
            scrape_options={"formats": ["markdown"]}
        )
        
        pages = result.data
        print(f"Raw pages returned for {category}: {len(pages)}")
        
        for page in pages:
            content = page.markdown or ""
            char_count = len(content)
            
            if char_count > 50:
                meta = page.metadata
                page_url = ""
                title = ""
                if meta:
                    page_url = getattr(meta, "source_url", "") or getattr(meta, "url", "") or ""
                    title = getattr(meta, "title", "") or ""
                
                all_pages.append({
                    "url": page_url,
                    "title": title,
                    "content": content,
                    "char_count": char_count,
                    "category": category
                })
                total_pages_crawled += 1
        
        print(f"Valid articles for {category}: {sum(1 for p in all_pages if p['category'] == category)}")
        
        time.sleep(1)
        
    except Exception as e:
        print(f"Error crawling {category}: {e}")

all_pages.sort(key=lambda x: x["char_count"], reverse=True)

total_chars = sum(p["char_count"] for p in all_pages)

output_path = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\kaoyan_round2.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_pages, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print(f"SUMMARY")
print(f"{'='*60}")
print(f"Total pages crawled: {total_pages_crawled}")
print(f"Total characters: {total_chars:,}")

categories = {}
for p in all_pages:
    cat = p["category"]
    if cat not in categories:
        categories[cat] = {"count": 0, "chars": 0}
    categories[cat]["count"] += 1
    categories[cat]["chars"] += p["char_count"]

print("\nBy category:")
for cat, stats in categories.items():
    print(f"  {cat}: {stats['count']} pages, {stats['chars']:,} chars")

print(f"\nSaved to: {output_path}")

print("\nTop 10 articles:")
for i, p in enumerate(all_pages[:10]):
    t = (p["title"] or "(no title)")[:50]
    u = (p["url"] or "(no url)")[:70]
    print(f"  {i+1}. [{p['char_count']:,} chars] [{p['category']}] {t} | {u}")