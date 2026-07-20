# -*- coding: utf-8 -*-
"""Debug: check what grad-war-room page actually loads"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    api_calls = []
    page.on("request", lambda req: api_calls.append(req.url) if "/api/" in req.url else None)
    
    api_responses = []
    page.on("response", lambda resp: api_responses.append({"url": resp.url, "status": resp.status, "body": resp.text()[:500] if resp.status == 200 else resp.status}) if "/api/" in resp.url else None)
    
    page.goto("http://localhost:3000/grad-war-room", wait_until="networkidle", timeout=30000)
    
    # Click on dark knowledge tab
    dark_tab = page.query_selector('button:has-text("暗知识")')
    if dark_tab:
        dark_tab.click()
        page.wait_for_timeout(3000)
    
    print("=== API Calls Made ===")
    for url in api_calls:
        print(f"  {url}")
    
    print(f"\n=== API Responses ({len(api_responses)}) ===")
    for r in api_responses:
        print(f"  [{r['status']}] {r['url']}")
        if isinstance(r.get('body'), str) and r['status'] == 200:
            print(f"    Body: {r['body'][:200]}")
    
    # Check page content for data
    content = page.content()
    has_data = "暗知识" in content or "dark" in content.lower()
    print(f"\nPage has dark knowledge content: {has_data}")
    print(f"Page content length: {len(content)}")
    
    # Screenshot
    page.screenshot(path="D:\\职业规划\\职业规划\\tests\\screenshots\\grad-war-room-debug.png", full_page=True)
    print("Screenshot saved")
    
    browser.close()
