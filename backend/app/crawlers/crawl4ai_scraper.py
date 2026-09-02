"""DEPRECATED — 请改用 Crawl4AIClient（app/crawlers/crawl4ai_client.py）。

本文件是 crawl4ai 集成初期的 ad-hoc 验证脚本，存在三处合规问题，已废弃：
1. 绕过 SSRF 校验：硬编码 kaoyan.com URL，未过 url_safety.validate_outbound_url
2. 绕过 PENDING 审核队列：直接落盘 real_data/crawl4ai_results.json，不入库
3. 模块级 asyncio.run：import 本模块即触发真实抓取

正式能力见 Crawl4AIClient（同步封装 + SSRF/robots/限速护栏 + 走审核队列的
调用方）。本文件仅保留作历史参考，不删除、不注册、不在任何路径被 import。
"""

import asyncio
import json

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig


async def scrape_kaoyan():
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        word_count_threshold=10,
        exclude_external_links=True,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = []
        urls = [
            "https://www.kaoyan.com/experience/",
            "https://www.kaoyan.com/news/list/1/9370",
            "https://www.kaoyan.com/news/list/1/3946",
        ]

        for url in urls:
            try:
                result = await crawler.arun(url=url, config=run_config)
                if result and result.markdown:
                    results.append(
                        {
                            "url": url,
                            "markdown": result.markdown[:5000],
                            "title": result.metadata.get("title", "") if result.metadata else "",
                        }
                    )
                else:
                    print(f"  {url}: no markdown returned")
            except Exception as e:
                print(f"  {url}: error - {e}")

        output = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\crawl4ai_results.json"
        with open(output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Fetched {len(results)} pages with Crawl4AI")
        for r in results:
            print(f'  {r["url"]}: {len(r["markdown"])} chars')


if __name__ == "__main__":
    asyncio.run(scrape_kaoyan())
