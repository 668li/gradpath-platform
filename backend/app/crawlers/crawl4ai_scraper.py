import asyncio
import json
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig

async def scrape_kaoyan():
    browser_config = BrowserConfig(headless=True)
    run_config = CrawlerRunConfig(
        word_count_threshold=10,
        exclude_external_links=True,
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        results = []
        urls = [
            'https://www.kaoyan.com/experience/',
            'https://www.kaoyan.com/news/list/1/9370',
            'https://www.kaoyan.com/news/list/1/3946',
        ]
        
        for url in urls:
            try:
                result = await crawler.arun(url=url, config=run_config)
                if result and result.markdown:
                    results.append({
                        'url': url,
                        'markdown': result.markdown[:5000],
                        'title': result.metadata.get('title', '') if result.metadata else '',
                    })
                else:
                    print(f'  {url}: no markdown returned')
            except Exception as e:
                print(f'  {url}: error - {e}')
        
        output = r'D:\职业规划\职业规划\backend\app\crawlers\real_data\crawl4ai_results.json'
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f'Fetched {len(results)} pages with Crawl4AI')
        for r in results:
            print(f'  {r["url"]}: {len(r["markdown"])} chars')

asyncio.run(scrape_kaoyan())
