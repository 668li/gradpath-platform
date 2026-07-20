# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    
    # Login
    page.goto("http://localhost:4001/login", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(1000)
    inputs = page.query_selector_all("input")
    if len(inputs) >= 2:
        inputs[0].fill("test2@example.com")
        inputs[1].fill("testpass123")
        for b in page.query_selector_all("button"):
            if "登录" in (b.text_content() or ""):
                b.click()
                break
    page.wait_for_timeout(5000)
    print(f"Login: {page.url}")
    
    # Go to grad-war-room
    page.goto("http://localhost:4001/grad-war-room", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(3000)
    
    # Get all text content
    body = page.inner_text("body")
    print(f"\nPage text (first 500 chars):")
    print(body[:500])
    
    # Check for specific elements
    print(f"\nElement check:")
    print(f"  Has '考研作战室': {'考研作战室' in body}")
    print(f"  Has '院校情报': {'院校情报' in body}")
    print(f"  Has '暗知识': {'暗知识' in body}")
    print(f"  Has '智能推荐': {'智能推荐' in body}")
    print(f"  Has '登录': {'登录' in body}")
    
    # Check buttons
    buttons = page.query_selector_all("button")
    print(f"\nButtons found: {len(buttons)}")
    for b in buttons[:10]:
        print(f"  Button: '{(b.text_content() or '').strip()[:30]}'")
    
    page.screenshot(path=r"D:\职业规划\职业规划\tests\screenshots\debug-grad-war-room.png", full_page=True)
    browser.close()
