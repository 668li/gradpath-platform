# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("http://localhost:3000/grad-war-room", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(3000)
    
    html = page.content()
    # Check for key elements
    has_login = "登录" in html
    has_war_room = "考研作战室" in html
    has_tabs = "院校情报" in html
    has_auth_guard = "校验登录" in html or "正在校验" in html
    has_loading = "LoadingState" in html
    
    print(f"Has '登录': {has_login}")
    print(f"Has '考研作战室': {has_war_room}")
    print(f"Has tabs (院校情报): {has_tabs}")
    print(f"Has auth guard message: {has_auth_guard}")
    print(f"HTML length: {len(html)}")
    
    # Check visible text
    body_text = page.inner_text("body")
    print(f"\nVisible text (first 500 chars):")
    print(body_text[:500])
    
    browser.close()
