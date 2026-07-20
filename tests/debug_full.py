# -*- coding: utf-8 -*-
"""Full Playwright debug: screenshot each step"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

SS_DIR = "D:\\职业规划\\职业规划\\tests\\screenshots"
os.makedirs(SS_DIR, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1280, "height": 900})
    page = ctx.new_page()
    
    console_msgs = []
    page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text[:300]}"))
    
    # 1. Homepage
    page.goto("http://localhost:3000", wait_until="networkidle", timeout=30000)
    page.screenshot(path=f"{SS_DIR}\\step1_home.png")
    print("Step 1: Homepage loaded")
    
    # 2. Navigate to grad-war-room  
    page.goto("http://localhost:3000/grad-war-room", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    page.screenshot(path=f"{SS_DIR}\\step2_war_room.png", full_page=True)
    print("Step 2: Grad war room loaded")
    
    # 3. Check buttons
    buttons = page.query_selector_all('button')
    print(f"Buttons found: {len(buttons)}")
    for btn in buttons[:10]:
        txt = btn.text_content() or ""
        print(f"  Button: '{txt.strip()}'")
    
    # 4. Click dark knowledge tab
    dark_btn = page.query_selector('button:has-text("暗知识")')
    if dark_btn:
        print("\nStep 3: Clicking dark knowledge tab...")
        dark_btn.click()
        page.wait_for_timeout(5000)
        page.screenshot(path=f"{SS_DIR}\\step3_dark.png", full_page=True)
    else:
        print("\nStep 3: Dark knowledge button NOT found!")
    
    # 5. Print console
    print(f"\nConsole messages ({len(console_msgs)}):")
    for m in console_msgs[:20]:
        print(f"  {m}")
    
    browser.close()
