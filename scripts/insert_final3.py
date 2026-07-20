#!/usr/bin/env python
"""Insert final entries into DARK_KNOWLEDGE list."""

# Read the generated entries
with open('final_entries2.py', 'r', encoding='utf-8') as f:
    entries = f.read()

# Read the original file
with open('backend/app/seed/seed_grad_intel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the DARK_KNOWLEDGE closing bracket
lines = content.split('\n')
dk_bracket_line = None
for i, line in enumerate(lines):
    if line.strip() == ']' and i > 7000:
        dk_bracket_line = i
        break

if not dk_bracket_line:
    print("ERROR: Could not find closing bracket")
    exit(1)

print(f"Closing bracket at line: {dk_bracket_line + 1}")

# Insert BEFORE the closing bracket
lines.insert(dk_bracket_line, entries)

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
stages = ['career', 'exam', 'mental', 'transfer', 'retest', 'school_selection', 'decision', 'preparation']
count = 0
for stage in stages:
    count += len(re.findall(r'\("' + stage + '"', list_text))

print(f"Total DARK_KNOWLEDGE entries: {count}")
