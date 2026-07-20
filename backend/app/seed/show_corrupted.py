import re

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find corrupted entries - first answer is just a quote mark
# The pattern is: "answers": [\n            ",\n
pattern = r'"answers": \[\s*\n\s*",\s*\n'
for m in re.finditer(pattern, content):
    pos = m.start()
    # Show context
    start = max(0, pos - 150)
    end = min(len(content), pos + 400)
    print('===CORRUPTED===')
    print(content[start:end])
    print('===END===')
    print()
