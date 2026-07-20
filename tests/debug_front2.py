# -*- coding: utf-8 -*-
"""Debug: check JS console errors on grad-war-room"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append({"type": msg.type, "text": msg.text[:200]}))
    
    errors = []
    page.on("pageerror", lambda err: errors.append(str(err)[:200]))
    
    api_calls = []
    api_responses = []
    page.on("request", lambda req: api_calls.append(req.url) if "/api/" in req.url else None)
    page.on("response", lambda resp: api_responses.append({"url": resp.url, "status": resp.status}) if "/api/" in resp.url else None)
    
    page.goto("http://localhost:3000/grad-war-room", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    
    # Check which tab is active
    active_tab = page.query_selector('button[aria-selected="true"]')
    print(f"Active tab: {active_tab.text_content() if active_tab else 'none'}")
    
    # Click dark knowledge tab
    dark_tab = page.query_selector('button:has-text("暗知识")')
    if dark_tab:
        print(f"Found dark tab, clicking...")
        dark_tab.click()
        page.wait_for_timeout(5000)
    
    print(f"\nAPI calls after tab click: {len(api_calls)}")
    for url in api_calls:
        print(f"  {url}")
    
    print(f"\nAPI responses: {len(api_responses)}")
    for r in api_responses:
        print(f"  [{r['status']}] {r['url']}")
    
    print(f"\nJS Console errors: {len([m for m in console_msgs if m['type'] == 'error'])}")
    for m in console_msgs:
        if m['type'] == 'error':
            print(f"  ERROR: {m['text']}")
        elif m['type'] == 'warning':
            print(f"  WARN: {m['text']}")
    
    print(f"\nPage errors: {len(errors)}")
    for e in errors:
        print(f"  {e}")
    
    browser.close()
