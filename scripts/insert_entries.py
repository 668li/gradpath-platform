#!/usr/bin/env python
"""Insert new DARK_KNOWLEDGE entries into the seed file."""

import re

# Read the generated entries
with open('new_dk_entries.py', 'r', encoding='utf-8') as f:
    entries1 = f.read()

with open('more_dk_entries.py', 'r', encoding='utf-8') as f:
    entries2 = f.read()

# Combine entries
all_entries = entries1 + entries2

# Read the original file
with open('backend/app/seed/seed_grad_intel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the closing bracket of DARK_KNOWLEDGE
# The list ends with ] on a line by itself
# We need to insert before that ]
lines = content.split('\n')
insert_line = None
for i, line in enumerate(lines):
    if line.strip() == ']' and i > 1300:  # After DARK_KNOWLEDGE starts
        # Check if this is the DARK_KNOWLEDGE closing bracket
        # by looking back for the last tuple
        for j in range(i-1, max(i-20, 1300), -1):
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
lines.insert(insert_line, all_entries)

# Write back
with open('backend/app/seed/seed_grad_intel.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("Entries inserted successfully")

# Count entries
count = 0
stages = ("career", "exam", "mental", "transfer", "retest", "school_selection", "decision", "preparation")
in_list = False
for line in lines:
    stripped = line.strip()
    if 'DARK_KNOWLEDGE = [' in line:
        in_list = True
        continue
    if in_list:
        for stage in stages:
            if stripped.startswith('("' + stage + '"'):
                count += 1
                break
        if stripped == ']':
            break

print(f"Total DARK_KNOWLEDGE entries after insert: {count}")
