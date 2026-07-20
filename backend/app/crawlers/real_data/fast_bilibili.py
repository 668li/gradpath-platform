import urllib.request, json, time, urllib.parse

keywords = ["考研数学复习", "考研英语复习", "考研政治复习", "考研复试面试", "考研调剂经验"]
results = []

for kw in keywords:
    encoded_kw = urllib.parse.quote(kw)
    url = f"https://api.bilibili.com/x/web-interface/search/type?keyword={encoded_kw}&search_type=video&page=1&pagesize=30"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json",
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        data = json.loads(resp.read())
        if data.get("code") == 0:
            items = data["data"].get("result", [])[:30]
            for v in items:
                results.append({
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
        time.sleep(3)
    except Exception as e:
        print(f"[ERR] {kw}: {e}")
        time.sleep(5)

output = r"D:\职业规划\职业规划\backend\app\crawlers\real_data\fast_bilibili.json"
with open(output, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print(f"\nTotal: {len(results)} videos saved to {output}")
