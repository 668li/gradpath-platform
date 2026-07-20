import json

with open('app/crawlers/real_data/firecrawl_scraped.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Show first article's markdown structure
a = data['articles'][0]
md = a['content']
lines = md.split('\n')
for i, line in enumerate(lines[:40]):
    stripped = line.strip()
    if stripped:
        print(f"{i}: {stripped[:120]}")

print(f"\nURL: {a['url']}")
print(f"Content length: {len(md)}")
