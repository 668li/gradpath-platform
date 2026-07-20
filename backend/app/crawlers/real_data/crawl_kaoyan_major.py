import os, json

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY
from firecrawl import FirecrawlApp
app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

print("Starting crawl of kaoyan.com/major with limit=50...")
result = app.crawl(
    "https://www.kaoyan.com/major",
    limit=50,
    scrape_options={"formats": ["markdown"]}
)

pages = result.data
print(f"Raw pages returned: {len(pages)}")

majors = []
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
        majors.append({
            "url": url,
            "title": title,
            "content": content,
            "char_count": char_count
        })

majors.sort(key=lambda x: x["char_count"], reverse=True)

output_path = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\major_crawled.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(majors, f, ensure_ascii=False, indent=2)

print(f"\nPages crawled: {len(pages)}")
print(f"Pages with content (>50 chars): {len(majors)}")
print(f"Total chars: {total_chars:,}")
print(f"Saved to: {output_path}")

for i, m in enumerate(majors[:10]):
    t = (m["title"] or "(no title)")[:60]
    u = (m["url"] or "(no url)")[:80]
    print(f"  {i+1}. [{m['char_count']:,} chars] {t} | {u}")
