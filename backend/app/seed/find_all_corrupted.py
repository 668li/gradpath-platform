import re

with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find all lines that are just a quote mark followed by comma
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == '","' or stripped == '",':
        # Check if this is inside an answers array
        for j in range(max(0, i-10), i):
            if 'answers' in lines[j]:
                # Find the title
                for k in range(max(0, j-20), j):
                    if 'title' in lines[k]:
                        print(f'Line {i+1}: {lines[k].strip()[:80]}')
                        break
                break
