# -*- coding: utf-8 -*-
import sys, ast
sys.stdout.reconfigure(encoding='utf-8')
path = r'D:\职业规划\职业规划\backend\app\crawlers\real_data\real_data_pipeline.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('\u201c', "'").replace('\u201d', "'")
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
try:
    ast.parse(content)
    print('SYNTAX OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR: {e.lineno}: {e.msg}')
