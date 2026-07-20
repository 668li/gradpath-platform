# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    failed = []
    page.on('response', lambda resp: failed.append({"url": resp.url, "status": resp.status}) if resp.status >= 400 else None)
    
    page.goto('http://localhost:4001/kaoyan/schools', wait_until='networkidle', timeout=15000)
    page.wait_for_timeout(3000)
    
    print(f"Failed requests: {len(failed)}")
    for f in failed:
        print(f"  [{f['status']}] {f['url'][:150]}")
    
    browser.close()
