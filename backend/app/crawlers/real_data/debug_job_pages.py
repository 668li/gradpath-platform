import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = await context.new_page()

        # Debug BOSS直聘
        url1 = "https://www.zhipin.com/web/geek/job?query=%E8%80%83%E7%A0%94%E5%BA%94%E5%B1%8A%E7%94%9F&city=100010000"
        await page.goto(url1, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path="D:/职业规划/职业规划/backend/app/crawlers/real_data/debug_zhipin.png", full_page=True)
        html1 = await page.content()
        with open("D:/职业规划/职业规划/backend/app/crawlers/real_data/debug_zhipin.html", "w", encoding="utf-8") as f:
            f.write(html1)
        print("BOSS直聘 HTML saved")

        # Debug 猎聘
        url2 = "https://www.liepin.com/zhaopin/?key=%E8%80%83%E7%A0%94%E5%BA%94%E5%B1%8A%E7%94%9F"
        await page.goto(url2, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(5000)
        await page.screenshot(path="D:/职业规划/职业规划/backend/app/crawlers/real_data/debug_liepin.png", full_page=True)
        html2 = await page.content()
        with open("D:/职业规划/职业规划/backend/app/crawlers/real_data/debug_liepin.html", "w", encoding="utf-8") as f:
            f.write(html2)
        print("猎聘 HTML saved")

        await browser.close()

asyncio.run(main())
