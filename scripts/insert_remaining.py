#!/usr/bin/env python
"""Insert remaining entries into DARK_KNOWLEDGE list."""

# Read the generated entries
with open('remaining_entries.py', 'r', encoding='utf-8') as f:
    remaining = f.read()

# Read the original file
with open('backend/app/seed/seed_grad_intel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the closing bracket of DARK_KNOWLEDGE
lines = content.split('\n')
insert_line = None
for i, line in enumerate(lines):
    if line.strip() == ']' and i > 8000:  # After the previously inserted entries
        # Check if this is the DARK_KNOWLEDGE closing bracket
        for j in range(i-1, max(i-20, 8000), -1):
            if lines[j].strip().endswith('),'):
                insert_line = i
                break
        if insert_line:
            break

if not insert_line:
    print("ERROR: Could not find DARK_KNOWLEDGE closing bracket")
    exit(1)

print(f"Inserting before line {insert_line + 1}")

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
