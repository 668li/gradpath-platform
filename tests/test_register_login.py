# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # 1. Try register
    page.goto('http://localhost:3000/register', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(1000)
    
    inputs = page.query_selector_all('input')
    if len(inputs) >= 3:
        inputs[0].fill('测试用户')
        inputs[1].fill('test2@example.com')
        inputs[2].fill('testpass123')
        page.wait_for_timeout(500)
        
        btn = page.query_selector('button[type="submit"]')
        if btn:
            btn.click()
            page.wait_for_timeout(3000)
            print(f'After register URL: {page.url}')
        else:
            # Try finding by text
            btns = page.query_selector_all('button')
            for b in btns:
                txt = b.text_content() or ''
                if '注册' in txt:
                    b.click()
                    page.wait_for_timeout(3000)
                    print(f'After register URL: {page.url}')
                    break
    
    # 2. If still on register, try login
    if '/register' in page.url:
        page.goto('http://localhost:3000/login', wait_until='networkidle', timeout=30000)
        page.wait_for_timeout(1000)
        
        inputs = page.query_selector_all('input')
        if len(inputs) >= 2:
            inputs[0].fill('test2@example.com')
            inputs[1].fill('testpass123')
            page.wait_for_timeout(500)
            
            btns = page.query_selector_all('button')
            for b in btns:
                txt = b.text_content() or ''
                if '登录' in txt:
                    b.click()
                    page.wait_for_timeout(3000)
                    print(f'After login URL: {page.url}')
                    break
    
    # 3. Go to grad-war-room
    page.goto('http://localhost:3000/grad-war-room', wait_until='networkidle', timeout=30000)
    page.wait_for_timeout(3000)
    page.screenshot(path=r'D:\职业规划\职业规划\tests\screenshots\war-room-logged-in.png', full_page=True)
    
    body = page.inner_text('body')
    print(f'Grad war room URL: {page.url}')
    print(f'Body text (first 500): {body[:500]}')
    
    browser.close()
