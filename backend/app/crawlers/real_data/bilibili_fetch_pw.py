"""Fetch 考研 Bilibili videos using Playwright browser automation."""
import json
import re
import time
import urllib.parse
from pathlib import Path

OUTPUT = Path(r"D:\职业规划\职业规划\backend\app\crawlers\real_data\bilibili_round2.json")

KEYWORDS = ["考研择校", "考研二战", "考研心态", "考研调剂经验", "考研上岸"]

def main():
    from playwright.sync_api import sync_playwright

    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="zh-CN",
        )
        page = context.new_page()

        # Warm up with homepage
        try:
            page.goto("https://www.bilibili.com", wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(2000)
            print("[warmup] homepage loaded")
        except Exception as e:
            print(f"[warmup] failed: {e}")

        for kw in KEYWORDS:
            search_url = f"https://search.bilibili.com/all?keyword={urllib.parse.quote(kw)}"
            print(f"\n[{kw}] navigating...")
            try:
                page.goto(search_url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(3000)

                # Extract video cards via JS
                items_data = page.evaluate("""() => {
                    const results = [];
                    document.querySelectorAll('a[href*="/video/"]').forEach(a => {
                        const href = a.href;
                        const title = a.getAttribute('title') || a.textContent.trim();
                        if (title && title.length > 5 && href.includes('/video/')) {
                            results.push({title, href});
                        }
                    });
                    return results;
                }""")

                seen_bvids = set()
                count = 0
                for d in items_data:
                    bvid_m = re.search(r"(BV\w+)", d.get("href", ""))
                    bvid = bvid_m.group(1) if bvid_m else ""
                    if not bvid or bvid in seen_bvids:
                        continue
                    seen_bvids.add(bvid)
                    results.append({
                        "title": d["title"][:200],
                        "author": "",
                        "views": 0,
                        "description": "",
                        "url": f"https://www.bilibili.com/video/{bvid}",
                        "bvid": bvid,
                        "keyword": kw,
                    })
                    count += 1
                    if count >= 10:
                        break

                print(f"[{kw}] extracted {count} videos")

            except Exception as e:
                print(f"[{kw}] error: {e}")

            time.sleep(1)

        browser.close()

    print(f"\nTotal videos found: {len(results)}")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Saved to {OUTPUT}")

if __name__ == "__main__":
    main()
