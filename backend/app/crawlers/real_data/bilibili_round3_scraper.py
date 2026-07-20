from playwright.sync_api import sync_playwright
import json, time, re

keywords = ["考研专业课", "考研调剂2025", "考研上岸经验", "考研数学真题", "考研英语真题"]
results = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    for kw in keywords:
        page = ctx.new_page()
        try:
            page.goto(f"https://search.bilibili.com/all?keyword={kw}", wait_until="networkidle", timeout=20000)
            time.sleep(3)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2)
            links = page.query_selector_all('a[href*="/video/BV"]')
            seen = set()
            for link in links:
                href = link.get_attribute("href") or ""
                text = (link.text_content() or "").strip()
                bvid = re.search(r'BV[a-zA-Z0-9]+', href)
                if bvid and bvid.group() not in seen and text and len(text) > 3:
                    seen.add(bvid.group())
                    results.append({"title": text[:200], "url": href, "bvid": bvid.group(), "keyword": kw})
        except Exception as e:
            print(f"Error for {kw}: {e}")
        finally:
            page.close()
            time.sleep(2)
    browser.close()

with open(r"D:\职业规划\职业规划\backend\app\crawlers\real_data\bilibili_round3.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Total videos found: {len(results)}")
