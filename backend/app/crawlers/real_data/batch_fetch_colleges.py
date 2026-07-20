import httpx, asyncio, json, re, time

async def fetch_college(client, cid):
    try:
        resp = await client.get(f"https://www.kaoyan.com/college/overview?id={cid}", timeout=15)
        if resp.status_code == 200:
            text = re.sub(r'<[^>]+>', ' ', resp.text)
            text = re.sub(r'\s+', ' ', text).strip()
            return {"id": cid, "content": text[:2000]}
    except: pass
    return None

async def main():
    all_ids = list(range(1001, 1200)) + list(range(1300, 1500)) + list(range(1600, 1800))
    async with httpx.AsyncClient(headers={"User-Agent": "Mozilla/5.0"}) as client:
        results = []
        for i in range(0, len(all_ids), 10):
            batch = all_ids[i:i+10]
            tasks = [fetch_college(client, cid) for cid in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend([r for r in batch_results if r])
            await asyncio.sleep(0.5)
    
    output = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\college_loop.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Fetched {len(results)} colleges")

asyncio.run(main())