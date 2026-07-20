import asyncio
import json
import os
import time
from playwright.async_api import async_playwright

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "job_data.json")

KEYWORDS = ["考研应届生", "硕士毕业"]
SOURCES = [
    {"name": "BOSS直聘", "url": "https://www.zhipin.com/web/geek/job?query={kw}&city=100010000"},
    {"name": "猎聘", "url": "https://www.liepin.com/zhaopin/?key={kw}"},
]

async def scrape_zhipin(page, keyword):
    results = []
    url = f"https://www.zhipin.com/web/geek/job?query={keyword}&city=100010000"
    print(f"  [BOSS直聘] {keyword} -> {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        cards = await page.query_selector_all(".job-card-wrapper")
        if not cards:
            cards = await page.query_selector_all("[class*='job-card']")
        print(f"  [BOSS直聘] Found {len(cards)} cards for '{keyword}'")
        for card in cards[:20]:
            try:
                title_el = await card.query_selector(".job-name") or await card.query_selector("[class*='job-name']")
                company_el = await card.query_selector(".company-name a") or await card.query_selector("[class*='company-name']")
                salary_el = await card.query_selector(".salary") or await card.query_selector("[class*='salary']")
                area_el = await card.query_selector(".job-area") or await card.query_selector("[class*='job-area']")
                link_el = await card.query_selector("a[ka]")

                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                salary = (await salary_el.inner_text()).strip() if salary_el else ""
                area = (await area_el.inner_text()).strip() if area_el else ""
                link = ""
                if link_el:
                    href = await link_el.get_attribute("href")
                    link = f"https://www.zhipin.com{href}" if href and href.startswith("/") else href or ""

                if title:
                    results.append({
                        "title": title, "company": company, "salary": salary,
                        "area": area, "url": link, "keyword": keyword, "source": "BOSS直聘"
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"  [BOSS直聘] Error: {e}")
    return results


async def scrape_liepin(page, keyword):
    results = []
    url = f"https://www.liepin.com/zhaopin/?key={keyword}"
    print(f"  [猎聘] {keyword} -> {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)
        cards = await page.query_selector_all(".job-card") or await page.query_selector_all("[class*='job-card']")
        if not cards:
            cards = await page.query_selector_all("[class*='job-list-item']")
        if not cards:
            cards = await page.query_selector_all("[class*='job-card-pc']")
        print(f"  [猎聘] Found {len(cards)} cards for '{keyword}'")
        for card in cards[:20]:
            try:
                title_el = await card.query_selector("[class*='job-title'] a") or await card.query_selector("[class*='job-title']")
                company_el = await card.query_selector("[class*='company-name'] a") or await card.query_selector("[class*='company-name']")
                salary_el = await card.query_selector("[class*='job-salary']")
                area_el = await card.query_selector("[class*='job-dq']") or await card.query_selector("[class*='job-area']")

                title = (await title_el.inner_text()).strip() if title_el else ""
                company = (await company_el.inner_text()).strip() if company_el else ""
                salary = (await salary_el.inner_text()).strip() if salary_el else ""
                area = (await area_el.inner_text()).strip() if area_el else ""
                link = ""
                link_el = await card.query_selector("a[href]")
                if link_el:
                    href = await link_el.get_attribute("href")
                    link = f"https://www.liepin.com{href}" if href and href.startswith("/") else href or ""

                if title:
                    results.append({
                        "title": title, "company": company, "salary": salary,
                        "area": area, "url": link, "keyword": keyword, "source": "猎聘"
                    })
            except Exception:
                continue
    except Exception as e:
        print(f"  [猎聘] Error: {e}")
    return results


async def main():
    all_results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        for source in SOURCES:
            for kw in KEYWORDS:
                if source["name"] == "BOSS直聘":
                    results = await scrape_zhipin(page, kw)
                else:
                    results = await scrape_liepin(page, kw)
                all_results.extend(results)
                print(f"  -> collected {len(results)} jobs from {source['name']} for '{kw}'")
                await asyncio.sleep(2)

        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    total_chars = sum(len(json.dumps(r, ensure_ascii=False)) for r in all_results)
    print(f"\n=== Done ===")
    print(f"Total jobs: {len(all_results)}")
    print(f"Total chars: {total_chars}")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())
