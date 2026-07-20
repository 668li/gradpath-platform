# -*- coding: utf-8 -*-
import sys, ast, re
sys.stdout.reconfigure(encoding='utf-8')
path = r'D:\职业规划\职业规划\backend\app\crawlers\real_data\real_data_pipeline.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace regular double quotes inside "title": "..." values
# Find pattern: "title": "...inner"..." 
lines = content.split('\n')
for i, line in enumerate(lines):
    if '"title":' in line and line.count('"') > 6:
        # Fix: replace inner double quotes in the title value
        idx = line.find('"title":')
        if idx >= 0:
            rest = line[idx + len('"title":'):]
            # Find first " (opening of value)
            first_q = rest.find('"')
            if first_q >= 0:
                after_first = rest[first_q + 1:]
                # Find last " before ,
                last_q = after_first.rfind('",')
                if last_q >= 0:
                    inner = after_first[:last_q]
                    if '"' in inner:
                        new_inner = inner.replace('"', "'")
                        lines[i] = line[:idx + len('"title":')] + ' "' + new_inner + '",' + after_first[last_q + 2:]

content = '\n'.join(lines)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

try:
    ast.parse(content)
    print('SYNTAX OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e.lineno}: {e.msg}')
