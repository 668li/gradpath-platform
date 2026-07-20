import os, json, time

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")
if not FIRECRAWL_API_KEY:
    print("[WARN] FIRECRAWL_API_KEY 环境变量未设置，Firecrawl功能不可用")
os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY
from firecrawl import FirecrawlApp
from firecrawl.v2.types import PaginationConfig

app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

sections = {
    "考研动态": "https://yz.chsi.com.cn/kyzx/kydt/",
    "教育部政策": "https://yz.chsi.com.cn/kyzx/jybzc/",
    "招生简章": "https://yz.chsi.com.cn/kyzx/zsjz/",
    "复试经验": "https://yz.chsi.com.cn/kyzx/fstj/",
}

results = {}
summary = {}
total_chars = 0

for name, url in sections.items():
    print(f"\n=== Starting crawl: {name} ({url}) ===", flush=True)
    try:
        job = app.start_crawl(url, limit=50)
        job_id = job.id if hasattr(job, 'id') else job.get('id')
        print(f"  Job started: {job_id}", flush=True)

        while True:
            status = app.get_crawl_status(job_id)
            state = status.status if hasattr(status, 'status') else status.get('status', '')
            total = getattr(status, 'total', 0) or 0
            completed = getattr(status, 'completed', 0) or 0
            print(f"  Status: {state} ({completed}/{total})", flush=True)

            if state in ('completed', 'failed', 'canceled'):
                break
            time.sleep(10)

        if state == 'failed':
            error = getattr(status, 'error', 'unknown')
            print(f"  FAILED: {error}", flush=True)
            results[name] = {"error": str(error)}
            summary[name] = {"pages": 0, "chars": 0, "error": str(error)}
            continue

        all_pages = []
        pc = PaginationConfig(auto_paginate=True, max_results=200, max_pages=10)
        status = app.get_crawl_status(job_id, pagination_config=pc)

        all_data = status.data if hasattr(status, 'data') else []
        if all_data:
            all_pages.extend(all_data)

        print(f"  Retrieved {len(all_pages)} pages", flush=True)

        char_count = 0
        entries = []
        for p in all_pages:
            content = ""
            if hasattr(p, "markdown"):
                content = p.markdown or ""
            elif isinstance(p, dict):
                content = p.get("markdown", "") or p.get("content", "") or ""

            title = ""
            source_url = ""
            if hasattr(p, "metadata") and p.metadata:
                title = getattr(p.metadata, "title", "") or ""
                source_url = getattr(p.metadata, "sourceURL", "") or ""
            elif isinstance(p, dict) and "metadata" in p:
                title = p["metadata"].get("title", "")
                source_url = p["metadata"].get("sourceURL", "")

            char_count += len(content)
            entries.append({
                "url": source_url,
                "title": title,
                "content": content,
                "content_length": len(content),
            })

        results[name] = entries
        summary[name] = {"pages": len(all_pages), "chars": char_count}
        total_chars += char_count
        print(f"  Done: {len(all_pages)} pages, {char_count} chars", flush=True)
    except Exception as e:
        import traceback; traceback.print_exc()
        results[name] = {"error": str(e)}
        summary[name] = {"pages": 0, "chars": 0, "error": str(e)}

output = {
    "summary": summary,
    "total_pages": sum(s.get("pages", 0) for s in summary.values()),
    "total_chars": total_chars,
    "data": results,
}

out_path = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\yz_crawled.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n=== SUMMARY ===", flush=True)
for name, s in summary.items():
    print(f"  {name}: {s.get('pages',0)} pages, {s.get('chars',0)} chars", flush=True)
print(f"  TOTAL: {output['total_pages']} pages, {total_chars} chars", flush=True)
print(f"\nSaved to: {out_path}", flush=True)
