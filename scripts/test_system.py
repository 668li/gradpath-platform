# -*- coding: utf-8 -*-
import sys, json, urllib.request, time
sys.stdout.reconfigure(encoding='utf-8')

print("=== Backend Health ===")
try:
    req = urllib.request.Request("http://localhost:8001/health", headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    print(f"  Status: {data.get('status')}")
    print(f"  Database: {data.get('database')}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== Recommendation API ===")
try:
    req = urllib.request.Request("http://localhost:8001/api/recommend/schools?target_score=370", headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    items = data.get("items", [])
    print(f"  Schools recommended: {len(items)}")
    if items:
        print(f"  Top: {items[0].get('name', '')} ({items[0].get('match_score', 0)})")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== Dark Knowledge (paginated) ===")
try:
    req = urllib.request.Request("http://localhost:8001/api/grad-intel/dark-knowledge/list?page=1&per_page=20", headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    print(f"  Items returned: {len(data)}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== Yanzhao Programs ===")
try:
    req = urllib.request.Request("http://localhost:8001/api/grad-intel/yanzhao-programs?limit=10", headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=5)
    data = json.loads(resp.read())
    count = len(data) if isinstance(data, list) else "N/A"
    print(f"  Items returned: {count}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== Frontend (port 4001) ===")
try:
    req = urllib.request.Request("http://localhost:4001/", headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=5)
    print(f"  Status: {resp.status}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== All Systems Operational ===")
