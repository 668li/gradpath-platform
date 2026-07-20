#!/usr/bin/env python
"""Fix: Remove incorrectly inserted entries and insert them BEFORE the closing bracket."""

# Read the file
with open('backend/app/seed/seed_grad_intel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the DARK_KNOWLEDGE closing bracket
# First, find the start
dk_start = content.index('DARK_KNOWLEDGE = [')

# Find the correct closing bracket by counting brackets from the start
bracket_count = 0
in_list = False
dk_end = dk_start
for i, ch in enumerate(content[dk_start:]):
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
                dk_end = dk_start + i + 1
                break

# Find the line number of dk_end
lines_before = content[:dk_end].count('\n')
print(f"DARK_KNOWLEDGE list ends at line: {lines_before + 1}")

# Find what's after the closing bracket
lines = content.split('\n')
print(f"Line {lines_before}: {lines[lines_before-1][:80] if lines_before > 0 else 'N/A'}")
print(f"Line {lines_before+1}: {lines[lines_before][:80] if lines_before < len(lines) else 'N/A'}")

# Check if entries were inserted after the bracket
# If line after ] starts with ("career" etc., they were inserted incorrectly
if lines[lines_before].strip().startswith('("career"') or lines[lines_before].strip().startswith('("exam"'):
    print("ERROR: Entries were inserted AFTER the closing bracket!")
    print("Need to move them BEFORE the bracket.")
    
    # Find where the incorrectly inserted entries end
    # They should end before the next function definition
    insert_end = lines_before + 1
    for i in range(lines_before + 1, len(lines)):
        if lines[i].strip().startswith('def ') or lines[i].strip().startswith('# '):
            insert_end = i
            break
    if insert_end == lines_before + 1:
        insert_end = len(lines)
    
    print(f"Incorrectly inserted entries from line {lines_before+1} to {insert_end}")
    
    # Extract the incorrectly inserted entries
    incorrect_entries = '\n'.join(lines[lines_before:insert_end])
    
    # Remove the incorrectly inserted entries
    new_lines = lines[:lines_before] + lines[insert_end:]
    
    # Now insert them BEFORE the closing bracket
    # The closing bracket is now at index lines_before-1 (since we removed entries after it)
    new_lines.insert(lines_before, incorrect_entries)
    
    # Write back
    with open('backend/app/seed/seed_grad_intel.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print("Fixed! Entries moved before the closing bracket.")
else:
    print("Entries are in the correct position.")
