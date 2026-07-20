# -*- coding: utf-8 -*-
import sys, json
sys.stdout.reconfigure(encoding='utf-8')

path = 'D:/职业规划/职业规划/backend/app/crawlers/real_data/yz_crawled.json'
with open(path, encoding='utf-8') as f:
    data = json.load(f)
for section, pages in data['data'].items():
    print(f'{section}: type={type(pages).__name__}, len={len(pages)}')
    if isinstance(pages, dict):
        first_key = list(pages.keys())[0] if pages else None
        print(f'  First key: {first_key}')
        if first_key:
            item = pages[first_key]
            print(f'  Type of first item: {type(item).__name__}')
            if isinstance(item, dict):
                print(f'  Keys: {list(item.keys())[:5]}')
    elif isinstance(pages, list) and pages:
        print(f'  First item keys: {list(pages[0].keys())}')
