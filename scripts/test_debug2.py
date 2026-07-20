# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    
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
    print("Login:", page.url)
    
    page.goto("http://localhost:4001/grad-war-room", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(5000)
    
    body = page.inner_text("body")
    print("Body length:", len(body))
    print("First 500:", body[:500])
    
    for t in ["院校情报", "自我定位", "暗知识", "智能推荐"]:
        status = "PASS" if t in body else "FAIL"
        print("  " + t + ": " + status)
    
    browser.close()
