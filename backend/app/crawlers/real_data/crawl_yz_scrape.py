import os, json, time

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY
from firecrawl import FirecrawlApp

app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

# First try map to get URLs
out_path = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\yz_crawled.json"
with open(out_path, "r", encoding="utf-8") as f:
    existing = json.load(f)

remaining = [
    ("招生简章", "https://yz.chsi.com.cn/kyzx/zsjz/"),
    ("复试经验", "https://yz.chsi.com.cn/kyzx/fstj/"),
]

for name, base_url in remaining:
    print(f"\n=== Trying map: {name} ({base_url}) ===", flush=True)
    try:
        map_result = app.map_url(base_url, limit=50)
        urls = map_result.links if hasattr(map_result, 'links') else []
        print(f"  Found {len(urls)} URLs via map", flush=True)
        
        entries = []
        char_count = 0
        for i, url in enumerate(urls):
            print(f"  Scraping {i+1}/{len(urls)}: {url}", flush=True)
            try:
                result = app.scrape_url(url)
                content = result.markdown or "" if hasattr(result, 'markdown') else ""
                title = getattr(result.metadata, "title", "") or "" if hasattr(result, 'metadata') and result.metadata else ""
                source_url = getattr(result.metadata, "sourceURL", "") or "" if hasattr(result, 'metadata') and result.metadata else url
                char_count += len(content)
                entries.append({
                    "url": source_url,
                    "title": title,
                    "content": content,
                    "content_length": len(content),
                })
                time.sleep(1)
            except Exception as e2:
                print(f"    Error scraping {url}: {e2}", flush=True)
                continue
        
        existing["data"][name] = entries
        existing["summary"][name] = {"pages": len(entries), "chars": char_count}
        print(f"  Done: {len(entries)} pages, {char_count} chars", flush=True)
    except Exception as e:
        import traceback; traceback.print_exc()
        # If map fails, try scraping known URL patterns
        print(f"  Map failed, trying scrape of base URL only", flush=True)
        try:
            result = app.scrape_url(base_url)
            content = result.markdown or "" if hasattr(result, 'markdown') else ""
            title = getattr(result.metadata, "title", "") or "" if hasattr(result, 'metadata') and result.metadata else ""
            entries = [{"url": base_url, "title": title, "content": content, "content_length": len(content)}]
            existing["data"][name] = entries
            existing["summary"][name] = {"pages": 1, "chars": len(content)}
        except Exception as e3:
            print(f"  Fallback scrape also failed: {e3}", flush=True)

existing["total_pages"] = sum(s.get("pages", 0) for s in existing["summary"].values())
existing["total_chars"] = sum(s.get("chars", 0) for s in existing["summary"].values())

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)
print(f"\n=== FINAL ===", flush=True)
for name, s in existing["summary"].items():
    print(f"  {name}: {s.get('pages',0)} pages, {s.get('chars',0)} chars", flush=True)
print(f"  TOTAL: {existing['total_pages']} pages, {existing['total_chars']} chars", flush=True)
