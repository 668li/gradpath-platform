import os, json

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

print("Starting crawl of kaoyan.com with limit=100...")
result = app.crawl(
    "https://www.kaoyan.com/",
    limit=100,
    scrape_options={"formats": ["markdown"]}
)

pages = result.data
print(f"Raw pages returned: {len(pages)}")

articles = []
total_chars = 0
for page in pages:
    content = page.markdown or ""
    char_count = len(content)
    total_chars += char_count

    if char_count > 50:
        meta = page.metadata
        url = ""
        title = ""
        if meta:
            url = getattr(meta, "source_url", "") or getattr(meta, "url", "") or ""
            title = getattr(meta, "title", "") or ""
        articles.append({
            "url": url,
            "title": title,
            "content": content,
            "char_count": char_count
        })

articles.sort(key=lambda x: x["char_count"], reverse=True)

output_path = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\kaoyan_crawled.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"Articles with content (>50 chars): {len(articles)}")
print(f"Total chars of real content: {total_chars:,}")
print(f"Saved to: {output_path}")

for i, a in enumerate(articles[:10]):
    t = (a["title"] or "(no title)")[:60]
    u = (a["url"] or "(no url)")[:80]
    print(f"  {i+1}. [{a['char_count']:,} chars] {t} | {u}")
