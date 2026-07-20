with open(r'D:\职业规划\职业规划\backend\app\seed\seed_kaoyan_community.py','r',encoding='utf-8') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}')
for i in range(37, 90):
    print(f'{i+1}: {lines[i].rstrip()}')
