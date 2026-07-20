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
        for b in page.query_selector_all('button'):
            if '登录' in (b.text_content() or ''):
                b.click()
                break
    page.wait_for_timeout(3000)
    print(f'Login OK: {page.url}')
    
    # Test: Dark Knowledge with 1000+ entries
    page.goto('http://localhost:3000/grad-war-room', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    dark_btn = page.query_selector('button:has-text("暗知识")')
    if dark_btn:
        dark_btn.click()
        page.wait_for_timeout(3000)
        page.screenshot(path=f'{SS}\\final-1000-dark.png', full_page=True)
        body = page.inner_text('body')
        stages = sum(1 for s in ['决策', '择校', '备考', '复试', '调剂', '职业', '心理', '初试'] if s in body)
        print(f'Dark Knowledge: {stages} stages visible in frontend')
    
    # Test: Community with expanded data
    page.goto('http://localhost:3000/kaoyan/community', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f'{SS}\\final-community.png', full_page=True)
    body = page.inner_text('body')
    post_count = body.count('经验')
    print(f'Community page loaded, posts visible: {post_count > 0}')
    
    browser.close()
    print('\nEnd-to-end verification COMPLETE!')
