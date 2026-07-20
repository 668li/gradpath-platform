# -*- coding: utf-8 -*-
"""Comprehensive Playwright test for GradPath - all pages"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright
import time, json

results = []

def test_page(browser, url, name, checks=None):
    page = browser.new_page()
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    try:
        start = time.time()
        resp = page.goto(url, wait_until="networkidle", timeout=30000)
        load_time = time.time() - start
        status = resp.status if resp else 0
        content = page.content()
        title = page.title()
        
        result = {"name": name, "url": url, "status": status, "load_time": f"{load_time:.1f}s", "passed": status == 200}
        
        # Take screenshot
        import os
        safe_name = name.replace(' ', '_').replace('/', '_').lower()
        ss_path = f"D:\\职业规划\\职业规划\\tests\\screenshots\\{safe_name}.png"
        os.makedirs(os.path.dirname(ss_path), exist_ok=True)
        page.screenshot(path=ss_path, full_page=True)
        result["screenshot"] = ss_path
        
        # Run specific checks
        if checks:
            for check_name, check_fn in checks.items():
                try:
                    passed = check_fn(page, content)
                    result[f"check_{check_name}"] = passed
                    if not passed:
                        result["passed"] = False
                except Exception as e:
                    result[f"check_{check_name}"] = False
                    result[f"error_{check_name}"] = str(e)[:100]
                    result["passed"] = False
        
        if console_errors:
            result["console_errors"] = len(console_errors)
        
        results.append(result)
        return result
    except Exception as e:
        result = {"name": name, "url": url, "status": "ERROR", "error": str(e)[:200], "passed": False}
        results.append(result)
        return result
    finally:
        page.close()

def has_text(page, content, text):
    return text in content

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        print("=" * 70)
        print("GradPath Comprehensive Test")
        print("=" * 70)
        
        # === Frontend Pages ===
        print("\n--- Frontend Pages ---")
        
        test_page(browser, "http://localhost:3000", "01-Homepage", {
            "has_title": lambda p, c: "GradPath" in c or "职径" in c,
            "has_nav": lambda p, c: "nav" in c.lower() or "header" in c.lower(),
        })
        
        test_page(browser, "http://localhost:3000/login", "02-Login", {
            "has_form": lambda p, c: "input" in c.lower() or "form" in c.lower(),
        })
        
        test_page(browser, "http://localhost:3000/dashboard", "03-Dashboard", {
            "loads": lambda p, c: len(c) > 1000,
        })
        
        test_page(browser, "http://localhost:3000/community", "04-Community", {
            "loads": lambda p, c: len(c) > 1000,
        })
        
        test_page(browser, "http://localhost:3000/kaoyan/community", "05-Kaoyan-Community", {
            "has_content": lambda p, c: len(c) > 1000,
        })
        
        test_page(browser, "http://localhost:3000/kaoyan/community/posts/new", "06-New-Post", {
            "loads": lambda p, c: len(c) > 1000,
        })
        
        test_page(browser, "http://localhost:3000/kaoyan/community/qa/new", "07-New-Question", {
            "loads": lambda p, c: len(c) > 1000,
        })
        
        test_page(browser, "http://localhost:3000/grad-war-room", "08-Grad-War-Room", {
            "loads": lambda p, c: len(c) > 1000,
        })
        
        test_page(browser, "http://localhost:3000/grad-charts", "09-Grad-Charts", {
            "loads": lambda p, c: len(c) > 1000,
        })
        
        test_page(browser, "http://localhost:3000/career", "10-Career", {
            "loads": lambda p, c: len(c) > 1000,
        })
        
        # === Backend API ===
        print("\n--- Backend API ---")
        
        test_page(browser, "http://localhost:8001/health", "API-Health")
        test_page(browser, "http://localhost:8001/ready", "API-Ready")
        test_page(browser, "http://localhost:8001/docs", "API-Swagger-Docs")
        test_page(browser, "http://localhost:8001/api/kaoyan/experience-posts", "API-Experience-Posts")
        test_page(browser, "http://localhost:8001/api/kaoyan/qa", "API-QA")
        test_page(browser, "http://localhost:8001/api/grad-intel/dark-knowledge", "API-Dark-Knowledge")
        test_page(browser, "http://localhost:8001/api/grad-intel/yanzhao-programs", "API-Yanzhao-Programs")
        test_page(browser, "http://localhost:8001/api/grad-intel/scorelines", "API-Scorelines")
        test_page(browser, "http://localhost:8001/api/grad-intel/adjustments", "API-Adjustments")
        
        browser.close()
        
        # === Print Results ===
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        passed = 0
        failed = 0
        for r in results:
            icon = "PASS" if r["passed"] else "FAIL"
            status_str = str(r.get("status", "N/A"))
            print(f"[{icon}] {r['name']}")
            print(f"  URL: {r['url']}")
            print(f"  HTTP: {status_str} | Load: {r.get('load_time', 'N/A')}")
            if "error" in r:
                print(f"  ERROR: {r['error']}")
            checks = {k:v for k,v in r.items() if k.startswith("check_")}
            if checks:
                for ck, cv in checks.items():
                    print(f"  {ck}: {'OK' if cv else 'FAIL'}")
            if r["passed"]:
                passed += 1
            else:
                failed += 1
        
        print(f"\n{'=' * 70}")
        print(f"TOTAL: {passed}/{passed+failed} passed, {failed} failed")
        print(f"{'=' * 70}")
        
        return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
