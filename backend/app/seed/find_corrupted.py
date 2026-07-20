import re

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find entries where first answer starts with just a quote
# Pattern: "answers": [\n            ",\n
pattern = r'"answers": \[\s*\n\s*",\s*\n'
matches = list(re.finditer(pattern, content))
print(f'Found {len(matches)} corrupted entries')

for m in matches:
    # Find the title
    pos = m.start()
    title_search = content.rfind('"title":', 0, pos)
    if title_search == -1:
        continue
    title_end = content.find('"', title_search + 9)
    title = content[title_search + 9:title_end]
    print(f'  - {title[:60]}')
