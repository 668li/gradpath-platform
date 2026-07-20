# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

# Check yz_crawled structure
path = 'D:/职业规划/职业规划/backend/app/crawlers/real_data/yz_crawled.json'
with open(path, encoding='utf-8') as f:
    data = json.load(f)
for section, pages in data['data'].items():
    print(f'{section}: {len(pages)} pages')
    if pages:
        p = pages[0]
        print(f'  Keys: {list(p.keys())}')
        title = p.get('title', '')
        content = p.get('content', '')
        print(f'  title: {title[:60]}')
        print(f'  content_len: {len(content)}')

# Check webfetch structure
print()
path2 = 'D:/职业规划/职业规划/backend/app/crawlers/real_data/webfetch_articles.json'
try:
    with open(path2, encoding='utf-8-sig') as f:
        data2 = json.load(f)
    if isinstance(data2, list) and len(data2) > 0:
        p = data2[0]
        print(f'webfetch: list, {len(data2)} items')
        print(f'  Keys: {list(p.keys())}')
        print(f'  title: {str(p.get("title",""))[:60]}')
    elif isinstance(data2, dict):
        print(f'webfetch: dict, keys={list(data2.keys())[:5]}')
except Exception as e:
    print(f'webfetch error: {e}')

# Check bilibili structure
print()
path3 = 'D:/职业规划/职业规划/backend/app/crawlers/real_data/bilibili_data.json'
with open(path3, encoding='utf-8') as f:
    data3 = json.load(f)
if 'videos' in data3:
    vids = data3['videos']
    print(f'bilibili: {len(vids)} videos')
    if vids:
        v = vids[0]
        print(f'  Keys: {list(v.keys())}')
        print(f'  title: {str(v.get("title",""))[:60]}')
