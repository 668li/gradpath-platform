# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    
    page.goto("http://localhost:4001/", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(3000)
    print(f"Root page URL: {page.url}")
    
    if "/login" in page.url:
        print("Redirected to login - CORRECT!")
        inputs = page.query_selector_all("input")
        if len(inputs) >= 2:
            inputs[0].fill("test2@example.com")
            inputs[1].fill("testpass123")
            for b in page.query_selector_all("button"):
                if "登录" in (b.text_content() or ""):
                    b.click()
                    break
            page.wait_for_timeout(5000)
            print(f"After login URL: {page.url}")
            
            page.goto("http://localhost:4001/grad-war-room", wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(3000)
            body = page.inner_text("body")
            for t in ["院校情报", "自我定位", "暗知识", "智能推荐"]:
                status = "PASS" if t in body else "FAIL"
                print(f"  Tab {t}: {status}")
    else:
        print(f"NOT redirected to login: {page.url}")
    
    browser.close()
    print("\nTest complete!")
