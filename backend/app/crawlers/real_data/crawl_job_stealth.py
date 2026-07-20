import asyncio
import json
import os
from playwright.async_api import async_playwright

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "job_data.json")

KEYWORDS = ["考研应届生", "硕士毕业"]

async def scrape_zhipin_stealth(context, keyword):
    results = []
    page = await context.new_page()
    url = f"https://www.zhipin.com/web/geek/job?query={keyword}&city=100010000"
    print(f"  [BOSS直聘] {keyword}")
    try:
        resp = await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(5000)
        # Check if login page
        content = await page.content()
        if "验证码登录" in content or "登录/注册" in content:
            print(f"  [BOSS直聘] Login required, trying API approach...")
            # Try the API directly
            api_url = f"https://www.zhipin.com/wapi/zpgeek/search/joblist.json?query={keyword}&city=100010000&page=1&pageSize=30"
            api_page = await context.new_page()
            await api_page.goto(api_url, wait_until="networkidle", timeout=30000)
            api_content = await api_page.content()
            print(f"  [BOSS直聘] API content length: {len(api_content)}")
            await api_page.close()

        # Try to find job cards on the main page
        cards = await page.query_selector_all("[class*='job-card']")
        print(f"  [BOSS直聘] Found {len(cards)} job cards")
        for card in cards[:20]:
            try:
                texts = await card.inner_text()
                lines = [l.strip() for l in texts.split('\n') if l.strip()]
                if len(lines) >= 2:
                    title = lines[0]
                    company = lines[1] if len(lines) > 1 else ""
                    salary = ""
                    area = ""
                    for l in lines:
                        if 'k' in l.lower() or '薪' in l or '-' in l and any(c.isdigit() for c in l):
                            salary = l
                        elif '区' in l or '市' in l or '省' in l:
                            area = l
                    if title:
                        results.append({
                            "title": title, "company": company, "salary": salary,
                            "area": area, "url": "", "keyword": keyword, "source": "BOSS直聘"
                        })
            except Exception:
                continue
    except Exception as e:
        print(f"  [BOSS直聘] Error: {e}")
    finally:
        await page.close()
    return results


async def scrape_liepin_stealth(context, keyword):
    results = []
    page = await context.new_page()
    url = f"https://www.liepin.com/zhaopin/?key={keyword}"
    print(f"  [猎聘] {keyword}")
    try:
        resp = await page.goto(url, wait_until="networkidle", timeout=45000)
        await page.wait_for_timeout(5000)
        final_url = page.url
        print(f"  [猎聘] Final URL: {final_url}")
        if "captcha" in final_url or "safe.liepin" in final_url:
            print(f"  [猎聘] CAPTCHA detected, skipping")
            return results

        cards = await page.query_selector_all("[class*='job-card']")
        if not cards:
            cards = await page.query_selector_all("[class*='job-list-item']")
        print(f"  [猎聘] Found {len(cards)} job cards")
        for card in cards[:20]:
            try:
                texts = await card.inner_text()
                lines = [l.strip() for l in texts.split('\n') if l.strip()]
                if len(lines) >= 2:
                    title = lines[0]
                    company = lines[1] if len(lines) > 1 else ""
                    salary = ""
                    area = ""
                    for l in lines:
                        if 'k' in l.lower() or '薪' in l or '-' in l and any(c.isdigit() for c in l):
                            salary = l
                        elif '区' in l or '市' in l or '省' in l:
                            area = l
                    if title:
                        results.append({
                            "title": title, "company": company, "salary": salary,
                            "area": area, "url": "", "keyword": keyword, "source": "猎聘"
                        })
            except Exception:
                continue
    except Exception as e:
        print(f"  [猎聘] Error: {e}")
    finally:
        await page.close()
    return results


async def scrape_51job(context, keyword):
    results = []
    page = await context.new_page()
    url = f"https://search.51job.com/list/000000,000000,0000,00,9,99,{keyword},2,1.html"
    print(f"  [前程无忧] {keyword}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        cards = await page.query_selector_all("[class*='j_joblist'] .e") or await page.query_selector_all(".joblist-box__item")
        if not cards:
            cards = await page.query_selector_all("[class*='joblist'] li")
        print(f"  [前程无忧] Found {len(cards)} cards")
        for card in cards[:20]:
            try:
                texts = await card.inner_text()
                lines = [l.strip() for l in texts.split('\n') if l.strip()]
                if lines:
                    title = lines[0]
                    company = lines[1] if len(lines) > 1 else ""
                    salary = ""
                    area = ""
                    for l in lines:
                        if 'k' in l.lower() or '薪' in l or '-' in l and any(c.isdigit() for c in l):
                            salary = l
                        elif '区' in l or '市' in l or '省' in l:
                            area = l
                    if title:
                        results.append({
                            "title": title, "company": company, "salary": salary,
                            "area": area, "url": "", "keyword": keyword, "source": "前程无忧"
                        })
            except Exception:
                continue
    except Exception as e:
        print(f"  [前程无忧] Error: {e}")
    finally:
        await page.close()
    return results


async def scrape_zhilian(context, keyword):
    results = []
    page = await context.new_page()
    url = f"https://sou.zhaopin.com/?jl=530&kw={keyword}&p=1"
    print(f"  [智联招聘] {keyword}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)
        cards = await page.query_selector_all("[class*='positionlist'] .clearfix") or await page.query_selector_all("[class*='joblist'] .joblist-box__item")
        if not cards:
            cards = await page.query_selector_all("[class*='jobCard']")
        print(f"  [智联招聘] Found {len(cards)} cards")
        for card in cards[:20]:
            try:
                texts = await card.inner_text()
                lines = [l.strip() for l in texts.split('\n') if l.strip()]
                if lines:
                    title = lines[0]
                    company = lines[1] if len(lines) > 1 else ""
                    salary = ""
                    area = ""
                    for l in lines:
                        if 'k' in l.lower() or '薪' in l or '-' in l and any(c.isdigit() for c in l):
                            salary = l
                        elif '区' in l or '市' in l or '省' in l:
                            area = l
                    if title:
                        results.append({
                            "title": title, "company": company, "salary": salary,
                            "area": area, "url": "", "keyword": keyword, "source": "智联招聘"
                        })
            except Exception:
                continue
    except Exception as e:
        print(f"  [智联招聘] Error: {e}")
    finally:
        await page.close()
    return results


async def main():
    all_results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )

        scrapers = [
            ("BOSS直聘", scrape_zhipin_stealth),
            ("猎聘", scrape_liepin_stealth),
            ("前程无忧", scrape_51job),
            ("智联招聘", scrape_zhilian),
        ]

        for name, scraper in scrapers:
            for kw in KEYWORDS:
                try:
                    results = await scraper(context, kw)
                    all_results.extend(results)
                    print(f"  -> {name}/{kw}: {len(results)} jobs")
                except Exception as e:
                    print(f"  -> {name}/{kw}: FAILED {e}")
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
