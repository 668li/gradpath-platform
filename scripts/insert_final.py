#!/usr/bin/env python
"""Insert remaining entries into DARK_KNOWLEDGE list."""

# Read the generated entries
with open('remaining_entries.py', 'r', encoding='utf-8') as f:
    remaining = f.read()

# Read the original file
with open('backend/app/seed/seed_grad_intel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the closing bracket at line 7231
lines = content.split('\n')
insert_line = 7231  # 0-indexed: line 7231 in 1-indexed = index 7230

print(f"Inserting before line {insert_line}")

# Insert the entries
lines.insert(insert_line, remaining)

# Write back
with open('backend/app/seed/seed_grad_intel.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Entries inserted successfully")

# Count entries
import re
with open('backend/app/seed/seed_grad_intel.py', encoding='utf-8') as f:
    content = f.read()

start = content.index('DARK_KNOWLEDGE = [')
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
tuples = re.findall(r'^\s*\("(career|exam|mental|transfer|retest|school_selection|decision|preparation)"', list_text, re.MULTILINE)
print(f"Total DARK_KNOWLEDGE entries: {len(tuples)}")
