import urllib.request, json, time, urllib.parse, http.cookiejar, re

# Load existing results
with open(r"D:\职业规划\职业规划\backend\app\crawlers\real_data\fast_bilibili.json", "r", encoding="utf-8") as f:
    existing = json.load(f)

# Set up cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

retry_keywords = ["考研数学复习", "考研复试面试"]

for kw in retry_keywords:
    try:
        # Step 1: Visit the search page to get cookies (including buvid3)
        search_page_url = f"https://search.bilibili.com/all?keyword={urllib.parse.quote(kw)}"
        page_req = urllib.request.Request(search_page_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        opener.open(page_req, timeout=15)
        time.sleep(2)

        # Step 2: Now call the API with cookies
        api_url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={urllib.parse.quote(kw)}&search_type=video&page=1&pagesize=30"
        api_req = urllib.request.Request(api_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Referer": f"https://search.bilibili.com/all?keyword={urllib.parse.quote(kw)}",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        resp = opener.open(api_req, timeout=15)
        data = json.loads(resp.read())

        if data.get("code") == 0:
            items = data["data"].get("result", [])[:30]
            for v in items:
                existing.append({
                    "title": v.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
                    "author": v.get("author", ""),
                    "views": v.get("play", 0),
                    "description": v.get("description", ""),
                    "url": f"https://www.bilibili.com/video/{v.get('bvid', '')}",
                    "keyword": kw
                })
            print(f"[OK] {kw}: got {len(items)} videos")
        else:
            print(f"[WARN] {kw}: API code={data.get('code')}, msg={data.get('message', '')}")

        time.sleep(4)
    except Exception as e:
        print(f"[ERR] {kw}: {e}")
        time.sleep(5)

output = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\fast_bilibili.json"
with open(output, "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)
print(f"\nTotal: {len(existing)} videos saved to {output}")
