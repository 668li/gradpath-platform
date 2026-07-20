# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

SS = r'D:\职业规划\职业规划\tests\screenshots'

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    
    # Login
    page.goto('http://localhost:3000/login', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(1000)
    inputs = page.query_selector_all('input')
    if len(inputs) >= 2:
        inputs[0].fill('test2@example.com')
        inputs[1].fill('testpass123')
        btns = page.query_selector_all('button')
        for b in btns:
            if '登录' in (b.text_content() or ''):
                b.click()
                break
    page.wait_for_timeout(3000)
    print(f'Login: {page.url}')
    
    # Test 1: Grad War Room - Dark Knowledge with expanded data
    page.goto('http://localhost:3000/grad-war-room', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    dark_btn = page.query_selector('button:has-text("暗知识")')
    if dark_btn:
        dark_btn.click()
        page.wait_for_timeout(3000)
        page.screenshot(path=f'{SS}\\final-dark-knowledge.png', full_page=True)
        body = page.inner_text('body')
        stages = sum(1 for s in ['决策', '择校', '备考', '复试', '调剂', '职业', '心理'] if s in body)
        print(f'Dark Knowledge: {stages} stages visible')
    
    # Test 2: Crawler Dashboard
    page.goto('http://localhost:3000/admin/crawlers', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f'{SS}\\final-crawler-dashboard.png', full_page=True)
    print(f'Crawler dashboard: loaded')
    
    # Test 3: Kaoyan Schools (more schools)
    page.goto('http://localhost:3000/kaoyan/schools', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f'{SS}\\final-schools.png', full_page=True)
    body = page.inner_text('body')
    has_data = '大学' in body
    print(f'Schools page: has data = {has_data}')
    
    # Test 4: API data verification
    import urllib.request, json
    endpoints = {
        'Dark Knowledge': 'http://localhost:8001/api/grad-intel/dark-knowledge/list',
        'Yanzhao Programs': 'http://localhost:8001/api/grad-intel/yanzhao-programs',
        'Scorelines': 'http://localhost:8001/api/grad-intel/scorelines',
        'Adjustments': 'http://localhost:8001/api/grad-intel/adjustments',
        'Experience Posts': 'http://localhost:8001/api/kaoyan/experience-posts',
        'QA': 'http://localhost:8001/api/kaoyan/qa',
    }
    
    print('\nAPI Data:')
    for name, url in endpoints.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=5)
            data = json.loads(resp.read())
            if isinstance(data, list):
                count = len(data)
            elif isinstance(data, dict) and 'items' in data:
                count = len(data['items'])
            else:
                count = len(data)
            print(f'  {name}: {count}')
        except Exception as e:
            print(f'  {name}: ERROR - {str(e)[:60]}')
    
    browser.close()
    print('\nAll verification complete!')
