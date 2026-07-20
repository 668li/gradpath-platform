import json
with open('/app/app/crawlers/real_data/zhihu_playwright.json') as f:
    data = json.load(f)
for item in data:
    print(f"Title: {item['title']}")
    print(f"Content preview: {item['content'][:200]}")
    print("---")
