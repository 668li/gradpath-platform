# -*- coding: utf-8 -*-
import sys, json, urllib.request
sys.stdout.reconfigure(encoding='utf-8')

endpoints = [
    ("推荐院校", "http://localhost:8001/api/recommend/schools?target_score=370"),
    ("推荐调剂", "http://localhost:8001/api/recommend/adjustments?target_score=350"),
    ("推荐暗知识", "http://localhost:8001/api/recommend/dark-knowledge?stage=preparation"),
]

for name, url in endpoints:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        
        print(f"\n{'='*50}")
        print(f"{name}")
        print(f"{'='*50}")
        
        if "data" in data and "recommendations" in data["data"]:
            recs = data["data"]["recommendations"][:5]
            for r in recs:
                if "school_name" in r:
                    print(f"  {r['school_name']} [{r.get('tier','')}] - 匹配分: {r.get('match_score', 0)}")
                    reasons = r.get("reasons", [])
                    if reasons:
                        print(f"    原因: {reasons[0]}")
                elif "title" in r:
                    print(f"  [{r.get('importance','')}] {r['title']}")
                else:
                    print(f"  {json.dumps(r, ensure_ascii=False)[:200]}")
        else:
            print(f"  Response: {json.dumps(data, ensure_ascii=False)[:300]}")
    except Exception as e:
        print(f"\n{name}: ERROR - {e}")

# Also test DB count
print(f"\n{'='*50}")
print("数据库数据量")
print(f"{'='*50}")
try:
    req = urllib.request.Request("http://localhost:8001/health", headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=5)
    print(f"  Health: {resp.read().decode()[:200]}")
except Exception as e:
    print(f"  Health ERROR: {e}")
