#!/usr/bin/env python
"""Fix: Move entries from after ] to before ]."""

# Read the file
with open('backend/app/seed/seed_grad_intel.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines before fix: {len(lines)}")

# Find the DARK_KNOWLEDGE closing bracket
dk_bracket_line = None
for i, line in enumerate(lines):
    if line.strip() == ']' and i > 7000:
        dk_bracket_line = i
        break

if not dk_bracket_line:
    print("ERROR: Could not find closing bracket")
    exit(1)

print(f"Closing bracket at line: {dk_bracket_line + 1}")

# Check if entries are after the bracket
if lines[dk_bracket_line + 1].strip().startswith('("career"'):
    print("Entries are AFTER the bracket, need to move them BEFORE")
    
    # Find where the incorrectly inserted entries end (before the next function)
    insert_end = dk_bracket_line + 1
    for i in range(dk_bracket_line + 1, len(lines)):
        if lines[i].strip().startswith('def ') or lines[i].strip().startswith('# '):
            insert_end = i
            break
    if insert_end == dk_bracket_line + 1:
        insert_end = len(lines)
    
    print(f"Entries to move: lines {dk_bracket_line + 2} to {insert_end}")
    
    # Extract the incorrectly inserted entries
    incorrectly_inserted = lines[dk_bracket_line + 1:insert_end]
    print(f"Number of lines to move: {len(incorrectly_inserted)}")
    
    # Remove the incorrectly inserted entries
    new_lines = lines[:dk_bracket_line + 1] + lines[insert_end:]
    
    # Now insert them BEFORE the closing bracket
    # The closing bracket is now at index dk_bracket_line
    for j, entry_line in enumerate(incorrectly_inserted):
        new_lines.insert(dk_bracket_line + j, entry_line)
    
    # Write back
    with open('backend/app/seed/seed_grad_intel.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    print("Fixed! Entries moved before the closing bracket.")
    print(f"Total lines after fix: {len(new_lines)}")
else:
    print("Entries are in the correct position (before the bracket)")
