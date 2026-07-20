import asyncio
import json
import re
from html import unescape

from crawlee.crawlers import HttpCrawler, HttpCrawlingContext


async def main():
    results = []
    crawler = HttpCrawler()

    @crawler.router.default_handler
    async def handler(context: HttpCrawlingContext):
        url = context.request.url
        try:
            snapshot = await context.get_snapshot()
            html = snapshot.html

            title_m = re.search(r"<title>([^<]+)</title>", html)
            title = unescape(title_m.group(1).strip()) if title_m else ""

            text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
            text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"&[a-zA-Z]+;", " ", text)
            text = re.sub(r"&#\d+;", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            content = text[:5000]

            date_m = re.search(r"发布于\s*(\d{4}-\d{2}-\d{2})", html)
            date = date_m.group(1) if date_m else ""

            tags = re.findall(r'标签[：:]\s*([^\s<]+)', html)

            results.append({
                "url": url,
                "title": title,
                "content": content,
                "content_len": len(content),
                "date": date,
                "tags": tags,
            })
            print(f"[OK] {url} -> {len(content)} chars, date={date}")
        except Exception as e:
            print(f"[ERR] {url}: {e}")
            results.append({"url": url, "title": "", "content": "", "content_len": 0, "error": str(e)})

    uuids = [
        "eaff65cc5ef54fd985cb4124e553313e", "b98c4545c6c04894acaa4b387e10163f",
        "9136ab9b59de43028cc7e9a40c1add86", "597c8eae321d4ed58f44bc67cd709db6",
        "155389d37de04a9ba1853c20c4ca96cb", "83657fa4c9324e15a42146d96dd908ae",
        "6bcfa318d1c740dcbd629439ea08dcce", "c8475e93c19c42de8b35d6ee8773ab56",
        "4dad4702ad234d678469c36e9fd4fa4b", "ce00bd687e2347beabbf66f9ce4ea3b3",
        "913cae862d4a4643994bdd6511c00abe", "6d76e2b9167d47b68e93906f04a2af93",
    ]
    start_urls = [f"https://www.kaoyan.com/experience/detail?uuid={u}" for u in uuids]

    print(f"Crawling {len(start_urls)} kaoyan.com experience pages...")
    await crawler.run(start_urls)

    output_path = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\crawlee_kaoyan.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = [r for r in results if r.get("content_len", 0) > 0]
    total_chars = sum(r["content_len"] for r in ok)
    print(f"\n=== DONE ===")
    print(f"Pages crawled: {len(results)}")
    print(f"With content: {len(ok)}")
    print(f"Total chars: {total_chars}")
    print(f"Saved to: {output_path}")


asyncio.run(main())
