# -*- coding: utf-8 -*-
"""真正从考研帮爬取经验帖的爬虫 - 使用Playwright"""
import sys, json, time, os, random
sys.stdout.reconfigure(encoding='utf-8')

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))

def scrape_kaoyan():
    """从kaoyan.com真正爬取经验帖"""
    from playwright.sync_api import sync_playwright
    
    results = []
    urls_to_try = [
        "https://www.kaoyan.com/exp/",
        "https://www.kaoyan.com/zhidao/",
        "https://www.kaoyan.com/news/",
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        
        for url in urls_to_try:
            page = ctx.new_page()
            try:
                print(f"Trying: {url}")
                resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
                if resp and resp.status == 200:
                    page.wait_for_timeout(3000)
                    content = page.content()
                    title = page.title()
                    text = page.inner_text("body")
                    print(f"  Status: {resp.status}, Title: {title}, Text length: {len(text)}")
                    
                    # Extract real text content
                    results.append({
                        "source": url,
                        "title": title,
                        "content_preview": text[:2000],
                        "url": url,
                    })
                    
                    # Try to find article links
                    links = page.query_selector_all("a[href]")
                    for link in links[:50]:
                        href = link.get_attribute("href") or ""
                        text_content = link.text_content() or ""
                        if text_content.strip() and len(text_content.strip()) > 5:
                            results.append({
                                "source": url,
                                "link_text": text_content.strip()[:200],
                                "href": href,
                            })
                else:
                    print(f"  Failed: status={resp.status if resp else 'None'}")
            except Exception as e:
                print(f"  Error: {str(e)[:100]}")
            finally:
                page.close()
                time.sleep(random.uniform(1, 3))
        
        browser.close()
    
    output_path = os.path.join(OUTPUT_DIR, "real_scraped_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\nTotal items scraped: {len(results)}")
    print(f"Saved to: {output_path}")
    return results

if __name__ == "__main__":
    scrape_kaoyan()
