#!/usr/bin/env python
"""Add one more entry to reach exactly 2000."""

# Read the file
with open('backend/app/seed/seed_grad_intel.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the DARK_KNOWLEDGE closing bracket
lines = content.split('\n')
dk_bracket_line = None
for i, line in enumerate(lines):
    if line.strip() == ']' and i > 15000:
        dk_bracket_line = i
        break

if not dk_bracket_line:
    print("ERROR: Could not find closing bracket")
    exit(1)

print(f"Closing bracket at line: {dk_bracket_line + 1}")

# One more entry
new_entry = '''    ("career", "读研规划", "研究生期间如何建立个人学术品牌的总结",
     "总结：1. 保持高质量的论文发表；2. 参加学术会议并做报告；3. 在专业社群中活跃；4. 维护个人学术主页；5. 与同行建立良好关系。个人品牌需要长期积累，但对职业发展很有价值。",
     "high", "个人品牌不重要", "个人品牌对职业发展很有价值", "从现在开始建立个人学术品牌"),
'''

# Insert BEFORE the closing bracket
lines.insert(dk_bracket_line, new_entry)

# Write back
with open('backend/app/seed/seed_grad_intel.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print("One more entry added")

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
