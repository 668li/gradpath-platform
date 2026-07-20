import json, re
with open('/app/app/crawlers/real_data/fast_colleges.json','r',encoding='utf-8') as f:
    d=json.load(f)

# Deep CSS strip
def deep_strip(text):
    text = re.sub(r'\{[^}]*\}', '', text)
    text = re.sub(r'[\w.-]+\s*:\s*[^;}{]+;', '', text)
    text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

for i, item in enumerate(d[:3]):
    content = item.get('content','')
    clean = deep_strip(content)
    print(f'Item {i} (id={item.get("id")}): {clean[:500]}')
    print()
