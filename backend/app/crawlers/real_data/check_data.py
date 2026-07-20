import json
with open(r"D:\职业规划\职业规划\backend\app\crawlers\real_data\yz_crawled.json", "r", encoding="utf-8") as f:
    d = json.load(f)
print("=== Summary ===")
for k, v in d["summary"].items():
    print(f"  {k}: {v}")
print(f"  Total: {d['total_pages']} pages, {d['total_chars']} chars")
print()
for section, pages in d["data"].items():
    if isinstance(pages, list) and pages:
        print(f"{section} sample titles:")
        for p in pages[:3]:
            t = p.get("title", "")[:60]
            print(f"  - {t}")
        print(f"  ({len(pages)} pages total)")
    else:
        print(f"{section}: no data")
    print()
