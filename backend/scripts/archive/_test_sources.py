import httpx
import json

targets = {
    "bilibili_api": "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=考研&page=1",
    "github_api": "https://api.github.com/search/repositories?q=考研&per_page=1",
    "v2ex_api": "https://www.v2ex.com/api/topics/show.json?node_name=qna",
    "kaoyan_rss": "https://www.kaoyan.com/rss",
    "zhihu_api": "https://www.zhihu.com/api/v4/search_v3?t=general&q=考研",
}

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

for name, url in targets.items():
    try:
        with httpx.Client(timeout=10, follow_redirects=True) as client:
            r = client.get(url, headers=headers)
            print(f"{name}: {r.status_code} ({len(r.text)} bytes)")
    except Exception as e:
        print(f"{name}: ERROR {str(e)[:80]}")
