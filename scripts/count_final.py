#!/usr/bin/env python
"""Count DARK_KNOWLEDGE entries."""
import re

with open('backend/app/seed/seed_grad_intel.py', encoding='utf-8') as f:
    content = f.read()

start = content.index('DARK_KNOWLEDGE = [')

# Find the end by counting brackets
bracket_count = 0
in_list = False
end = start
for i, ch in enumerate(content[start:]):
    if ch == '[' and not in_list:
        in_list = True
        bracket_count = 1
        continue
    if in_list:
        if ch == '[':
            bracket_count += 1
        elif ch == ']':
            bracket_count -= 1
            if bracket_count == 0:
                end = start + i + 1
                break

list_text = content[start:end]

# Count tuples
stages = ['career', 'exam', 'mental', 'transfer', 'retest', 'school_selection', 'decision', 'preparation']
count = 0
for stage in stages:
    count += len(re.findall(r'\("' + stage + '"', list_text))

print(f'Total DARK_KNOWLEDGE entries: {count}')
print(f'List length: {len(list_text)} chars')
