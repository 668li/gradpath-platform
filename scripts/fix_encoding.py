# -*- coding: utf-8 -*-
import sys, ast, re
sys.stdout.reconfigure(encoding='utf-8')
path = r'D:\职业规划\职业规划\backend\app\seed\seed_companies.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
replacements = {
    '\uff1a': ':', '\uff08': '(', '\uff09': ')', '\uff0c': ',',
    '\u3002': '.', '\uff01': '!', '\uff1f': '?', '\uff1b': ';',
    '\u201c': "'", '\u201d': "'", '\u2018': "'", '\u2019': "'",
    '\uff3b': '[', '\uff3d': ']', '\u3001': ',',
}
for old, new in replacements.items():
    content = content.replace(old, new)
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
try:
    ast.parse(content)
    print('SYNTAX OK')
except SyntaxError as e:
    print(f'SYNTAX ERROR at line {e.lineno}: {e.msg}')
