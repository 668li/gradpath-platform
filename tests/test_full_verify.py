# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    
    # Login first
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
    print(f'Logged in: {page.url}')
    
    # Go to grad-war-room
    page.goto('http://localhost:3000/grad-war-room', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=r'D:\职业规划\职业规划\tests\screenshots\war-room-1-intel.png', full_page=True)
    print('Tab 1: 院校情报 - loaded')
    
    # Click dark knowledge tab
    dark_btn = page.query_selector('button:has-text("暗知识")')
    if dark_btn:
        dark_btn.click()
        page.wait_for_timeout(3000)
        page.screenshot(path=r'D:\职业规划\职业规划\tests\screenshots\war-room-2-dark.png', full_page=True)
        body = page.inner_text('body')
        has_data = '决策' in body or '择校' in body or '备考' in body
        print(f'Tab 2: 暗知识 - loaded, has data: {has_data}')
        print(f'Body (first 300): {body[:300]}')
    else:
        print('Dark knowledge button not found!')
    
    # Click positioning tab
    pos_btn = page.query_selector('button:has-text("自我定位")')
    if pos_btn:
        pos_btn.click()
        page.wait_for_timeout(2000)
        page.screenshot(path=r'D:\职业规划\职业规划\tests\screenshots\war-room-3-positioning.png', full_page=True)
        print('Tab 3: 自我定位 - loaded')
    
    # Go to kaoyan community
    page.goto('http://localhost:3000/kaoyan/community', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=r'D:\职业规划\职业规划\tests\screenshots\kaoyan-community.png', full_page=True)
    body = page.inner_text('body')
    has_posts = '经验' in body or '帖子' in body
    print(f'Kaoyan community: loaded, has posts: {has_posts}')
    print(f'Body (first 300): {body[:300]}')
    
    # Go to kaoyan schools
    page.goto('http://localhost:3000/kaoyan/schools', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=r'D:\职业规划\职业规划\tests\screenshots\kaoyan-schools.png', full_page=True)
    body = page.inner_text('body')
    has_schools = '清华' in body or '大学' in body
    print(f'Kaoyan schools: loaded, has schools: {has_schools}')
    
    # Go to dashboard
    page.goto('http://localhost:3000/dashboard', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=r'D:\职业规划\职业规划\tests\screenshots\dashboard.png', full_page=True)
    print('Dashboard: loaded')
    
    browser.close()
    print('\nAll tests complete!')
