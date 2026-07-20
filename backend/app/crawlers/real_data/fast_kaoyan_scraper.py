import httpx, asyncio, json, os, re, time
from html import unescape

async def fetch_page(client, url):
    try:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        if resp.status_code == 200:
            return resp.text, resp.url
    except:
        pass
    return None, None

async def fetch_article(client, url, idx):
    try:
        resp = await client.get(url, follow_redirects=True, timeout=15)
        if resp.status_code == 200:
            title_m = re.search(r'<title>([^<]+)</title>', resp.text)
            title = unescape(title_m.group(1).strip()) if title_m else ""
            text = re.sub(r'<script[^>]*>.*?</script>', '', resp.text, flags=re.DOTALL)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
            return {"url": url, "title": title, "content": text[:3000], "idx": idx}
    except:
        pass
    return None

async def main():
    t0 = time.time()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
    async with httpx.AsyncClient(headers=headers) as client:
        all_uuids = []
        seen = set()
        
        # Try sitemap
        for sm_url in ["https://www.kaoyan.com/sitemap.xml", "https://www.kaoyan.com/robots.txt"]:
            html, _ = await fetch_page(client, sm_url)
            if html:
                uuids = re.findall(r'uuid=([a-f0-9]{32})', html)
                new = [u for u in uuids if u not in seen]
                seen.update(new)
                all_uuids.extend(new)
                print(f"{sm_url}: +{len(new)} UUIDs")
        
        # Try API-like endpoints
        api_patterns = [
            "https://www.kaoyan.com/api/experience/list",
            "https://www.kaoyan.com/api/article/list",
            "https://www.kaoyan.com/experience/api/list",
            "https://www.kaoyan.com/index.php?m=experience&a=index",
        ]
        for api_url in api_patterns:
            html, final_url = await fetch_page(client, api_url)
            if html:
                uuids = re.findall(r'[a-f0-9]{32}', html)
                new = [u for u in uuids if u not in seen]
                seen.update(new)
                all_uuids.extend(new)
                if new:
                    print(f"{api_url} -> {final_url}: +{len(new)} UUIDs (total: {len(all_uuids)})")
            await asyncio.sleep(0.2)

        # Try fetching category pages and extracting more links
        cat_urls = [
            "https://www.kaoyan.com/experience/",
            "https://www.kaoyan.com/",
        ]
        for cat_url in cat_urls:
            html, _ = await fetch_page(client, cat_url)
            if not html:
                continue
            # Find all links
            links = re.findall(r'href="([^"]+)"', html)
            # Also look for links in data attributes and JavaScript
            js_links = re.findall(r'["\']([^"\']*(?:article|post|detail|uuid)[^"\']*)["\']', html)
            all_found = links + js_links
            for link in all_found:
                link = unescape(link)
                if 'uuid=' in link:
                    uuid = re.search(r'uuid=([a-f0-9]{32})', link)
                    if uuid and uuid.group(1) not in seen:
                        seen.add(uuid.group(1))
                        all_uuids.append(uuid.group(1))
                elif re.search(r'/\d{5,}', link):
                    # Numeric article IDs
                    pass

        # Scan the HTML for any 32-char hex strings that look like UUIDs
        html, _ = await fetch_page(client, "https://www.kaoyan.com/experience/")
        if html:
            all_hex = re.findall(r'[a-f0-9]{32}', html)
            for h in all_hex:
                if h not in seen:
                    seen.add(h)
                    all_uuids.append(h)
        
        # Deduplicate
        all_uuids = list(dict.fromkeys(all_uuids))
        print(f"\nTotal unique UUIDs found: {len(all_uuids)}")
        
        target = min(50, len(all_uuids))
        print(f"Will fetch {target} articles")
        
        results = []
        for i in range(0, target, 10):
            batch = [f"https://www.kaoyan.com/experience/detail?uuid={u}" for u in all_uuids[i:i+10]]
            tasks = [fetch_article(client, url, i+j) for j, url in enumerate(batch)]
            batch_results = await asyncio.gather(*tasks)
            fetched = [r for r in batch_results if r]
            results.extend(fetched)
            print(f"Batch {i//10+1}: fetched {len(fetched)} (total: {len(results)})")
            if i + 10 < target:
                await asyncio.sleep(1)

        elapsed = time.time() - t0
        output = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\fast_kaoyan.json"
        with open(output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        total_chars = sum(len(r['content']) for r in results)
        print(f"\n=== RESULTS ===")
        print(f"Articles fetched: {len(results)}")
        print(f"Total chars: {total_chars}")
        print(f"Time: {elapsed:.1f}s")
        if elapsed > 0:
            print(f"Speed: {len(results)/elapsed:.1f} articles/sec")
        print(f"Saved to: {output}")

asyncio.run(main())
