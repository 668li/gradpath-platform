import json, re
with open('/app/app/crawlers/real_data/fast_colleges.json','r',encoding='utf-8') as f:
    d=json.load(f)
print('Total:', len(d))
for i, item in enumerate(d[:5]):
    content = item.get('content','')
    m = re.search(r'[\u4e00-\u9fff]{2,}(大学|学院|研究所)', content)
    if m:
        start = max(0, m.start()-5)
        snippet = content[start:m.end()+5]
        print(f'{i}: id={item.get("id")} -> found: {snippet}')
    else:
        print(f'{i}: id={item.get("id")} -> no college, first 200: {content[:200]}')
