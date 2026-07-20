import json

with open('app/crawlers/real_data/firecrawl_scraped.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

articles = data['articles']
print(f"Total articles: {len(articles)}")

cats = {}
for a in articles:
    cat = a.get('category', '?')
    cats[cat] = cats.get(cat, 0) + 1
print(f"Categories: {cats}")

good = 0
for a in articles:
    content = a.get('content', '')
    title = a.get('title', '')
    if len(content) > 200 and title != '未命名文章':
        good += 1
print(f"Good quality (content>200, titled): {good}/{len(articles)}")

for i, a in enumerate(articles[:8]):
    content_len = len(a.get('content', ''))
    title = a.get('title', '')[:60]
    print(f"  [{i+1}] {title} ({content_len} chars)")

# Check for short/empty content
short = [a for a in articles if len(a.get('content', '')) < 200]
print(f"\nShort content (<200 chars): {len(short)}")
for a in short[:3]:
    print(f"  - {a['title'][:40]}: {len(a.get('content',''))} chars")
