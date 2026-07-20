import urllib.request, json, time, urllib.parse, http.cookiejar

# Load existing results
with open(r"D:\职业规划\职业规划\backend\app\crawlers\real_data\fast_bilibili.json", "r", encoding="utf-8") as f:
    existing = json.load(f)

existing_bvids = {v["url"] for v in existing}

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

keywords = ["考研数学复习", "考研英语复习", "考研政治复习", "考研复试面试", "考研调剂经验"]
new_count = 0

for kw in keywords:
    try:
        # Fetch search page for cookies
        search_page_url = f"https://search.bilibili.com/all?keyword={urllib.parse.quote(kw)}"
        page_req = urllib.request.Request(search_page_url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })
        opener.open(page_req, timeout=15)
        time.sleep(1)

        # Fetch page 2
        api_url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={urllib.parse.quote(kw)}&search_type=video&page=2&pagesize=30"
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
            added = 0
            for v in items:
                bvid_url = f"https://www.bilibili.com/video/{v.get('bvid', '')}"
                if bvid_url not in existing_bvids:
                    existing.append({
                        "title": v.get("title", "").replace("<em class=\"keyword\">", "").replace("</em>", ""),
                        "author": v.get("author", ""),
                        "views": v.get("play", 0),
                        "description": v.get("description", ""),
                        "url": bvid_url,
                        "keyword": kw
                    })
                    existing_bvids.add(bvid_url)
                    added += 1
            print(f"[OK] {kw} page2: +{added} new (from {len(items)} results)")
            new_count += added
        else:
            print(f"[WARN] {kw} page2: API code={data.get('code')}, msg={data.get('message', '')}")

        time.sleep(4)
    except Exception as e:
        print(f"[ERR] {kw} page2: {e}")
        time.sleep(5)

output = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\fast_bilibili.json"
with open(output, "w", encoding="utf-8") as f:
    json.dump(existing, f, ensure_ascii=False, indent=2)
print(f"\nAdded {new_count} new videos. Total: {len(existing)} videos")
