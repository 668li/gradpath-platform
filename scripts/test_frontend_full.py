# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

SS = r"D:\职业规划\职业规划\tests\screenshots"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text[:200]) if msg.type == "error" else None)
    
    # 1. Login
    page.goto("http://localhost:4001/login", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    inputs = page.query_selector_all("input")
    if len(inputs) >= 2:
        inputs[0].fill("test2@example.com")
        inputs[1].fill("testpass123")
        for b in page.query_selector_all("button"):
            if "登录" in (b.text_content() or ""):
                b.click()
                break
    page.wait_for_timeout(5000)
    print(f"[1] Login: {page.url}")
    
    # 2. Dashboard
    page.goto("http://localhost:4001/dashboard", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{SS}\\final-dashboard.png", full_page=True)
    body = page.inner_text("body")
    print(f"[2] Dashboard: loaded, has_data={'院校' in body or '数据' in body}")
    
    # 3. Grad War Room - all 4 tabs
    page.goto("http://localhost:4001/grad-war-room", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(3000)
    
    tabs_found = {}
    for tab_name in ["院校情报", "自我定位", "暗知识", "智能推荐"]:
        for b in page.query_selector_all("button"):
            txt = (b.text_content() or "").strip()
            if tab_name in txt:
                tabs_found[tab_name] = True
                break
        else:
            tabs_found[tab_name] = False
    
    print(f"[3] Grad War Room tabs:")
    for tab, found in tabs_found.items():
        print(f"    {'PASS' if found else 'FAIL'} {tab}")
    
    # Click each tab
    for tab_name in ["院校情报", "暗知识", "智能推荐"]:
        for b in page.query_selector_all("button"):
            txt = (b.text_content() or "").strip()
            if tab_name in txt:
                b.click()
                page.wait_for_timeout(3000)
                page.screenshot(path=f"{SS}\\final-{tab_name}.png", full_page=True)
                print(f"    Screenshot saved: final-{tab_name}.png")
                break
    
    # 4. Community
    page.goto("http://localhost:4001/community", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{SS}\\final-community.png", full_page=True)
    body = page.inner_text("body")
    print(f"[4] Community: loaded, has_posts={'经验' in body or '帖子' in body}")
    
    # 5. Kaoyan Community
    page.goto("http://localhost:4001/kaoyan/community", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{SS}\\final-kaoyan.png", full_page=True)
    body = page.inner_text("body")
    print(f"[5] Kaoyan Community: loaded, has_data={'经验' in body or '问答' in body}")
    
    # 6. Schools
    page.goto("http://localhost:4001/kaoyan/schools", wait_until="networkidle", timeout=15000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{SS}\\final-schools.png", full_page=True)
    body = page.inner_text("body")
    print(f"[6] Schools: loaded, has_schools={'大学' in body}")
    
    # Console errors summary
    if console_errors:
        print(f"\nConsole errors: {len(console_errors)}")
        for e in console_errors[:5]:
            print(f"  {e[:100]}")
    else:
        print(f"\nConsole errors: 0 (clean)")
    
    browser.close()
    print("\n=== Frontend Test Complete ===")
