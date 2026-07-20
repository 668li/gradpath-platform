# -*- coding: utf-8 -*-
"""Playwright browser test for GradPath"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright
import time

results = []

def test_page(browser, url, name, expected_title_contains=None, take_screenshot=True):
    """Test a single page"""
    page = browser.new_page()
    try:
        start = time.time()
        response = page.goto(url, wait_until="networkidle", timeout=30000)
        load_time = time.time() - start
        
        status = response.status if response else "no response"
        title = page.title()
        content_len = len(page.content())
        
        # Check for errors
        errors = []
        page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
        
        result = {
            "name": name,
            "url": url,
            "status": status,
            "title": title,
            "load_time": f"{load_time:.2f}s",
            "content_length": content_len,
            "passed": status == 200
        }
        
        if expected_title_contains and expected_title_contains.lower() not in title.lower():
            result["passed"] = False
            result["error"] = f"Title '{title}' does not contain '{expected_title_contains}'"
        
        if take_screenshot:
            screenshot_path = f"D:\\职业规划\\职业规划\\tests\\screenshots\\{name.replace(' ', '_').lower()}.png"
            import os
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            page.screenshot(path=screenshot_path, full_page=True)
            result["screenshot"] = screenshot_path
        
        results.append(result)
        return result
        
    except Exception as e:
        result = {
            "name": name,
            "url": url,
            "status": "ERROR",
            "error": str(e)[:200],
            "passed": False
        }
        results.append(result)
        return result
    finally:
        page.close()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Test pages
        pages_to_test = [
            ("http://localhost:3000", "Homepage"),
            ("http://localhost:3000/login", "Login Page"),
            ("http://localhost:3000/dashboard", "Dashboard"),
            ("http://localhost:3000/community", "Community"),
            ("http://localhost:3000/kaoyan/community", "Kaoyan Community"),
            ("http://localhost:8001/health", "Backend Health"),
            ("http://localhost:8001/ready", "Backend Ready"),
        ]
        
        print("=" * 60)
        print("GradPath Playwright Browser Test")
        print("=" * 60)
        
        for url, name in pages_to_test:
            result = test_page(browser, url, name)
            status_icon = "PASS" if result["passed"] else "FAIL"
            print(f"\n[{status_icon}] {name}")
            print(f"  URL: {url}")
            print(f"  Status: {result.get('status', 'N/A')}")
            print(f"  Load Time: {result.get('load_time', 'N/A')}")
            print(f"  Title: {result.get('title', 'N/A')}")
            if "error" in result:
                print(f"  Error: {result['error']}")
            if "screenshot" in result:
                print(f"  Screenshot: {result['screenshot']}")
        
        # Summary
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        print(f"\n{'=' * 60}")
        print(f"Summary: {passed}/{total} passed")
        print(f"{'=' * 60}")
        
        browser.close()
        
        return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
