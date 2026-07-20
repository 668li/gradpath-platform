import sys

with open('backend/app/seed/seed_grad_intel.py', encoding='utf-8') as f:
    lines = f.readlines()

count = 0
in_list = False
end_line = 0
stages = ("career", "exam", "mental", "transfer", "retest", "school_selection", "decision", "preparation")

for i, line in enumerate(lines, 1):
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
            end_line = i
            break

print(f'Total DARK_KNOWLEDGE entries: {count}')
print(f'List closing bracket at line: {end_line}')
if end_line > 0:
    for j in range(end_line, min(end_line + 5, len(lines))):
        print(f'  Line {j+1}: {lines[j].rstrip()[:100]}')
