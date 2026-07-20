# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
path = r'D:\职业规划\职业规划\backend\app\seed\seed_grad_intel.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
count = content.count('created_by')
content = content.replace("        created_by='system',\n", "")
content = content.replace('        created_by="system",\n', "")
new_count = content.count('created_by')
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
print(f"Removed {count - new_count} created_by references. Remaining: {new_count}")
