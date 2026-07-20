#!/usr/bin/env python
"""Count DARK_KNOWLEDGE entries accurately."""
import re

with open('backend/app/seed/seed_grad_intel.py', encoding='utf-8') as f:
    content = f.read()

# Find DARK_KNOWLEDGE list
start = content.index('DARK_KNOWLEDGE = [')

# Find the end of the list by counting brackets
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
tuples = re.findall(r'^\s*\("(career|exam|mental|transfer|retest|school_selection|decision|preparation)"', list_text, re.MULTILINE)
print(f'Total DARK_KNOWLEDGE entries: {len(tuples)}')

# Find closing bracket line
lines = content.split('\n')
for i, line in enumerate(lines):
    if i > 1300 and line.strip() == ']':
        print(f'Closing bracket at line: {i + 1}')
        break
