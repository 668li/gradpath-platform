# -*- coding: utf-8 -*-
import sys, json, urllib.request, time
sys.stdout.reconfigure(encoding='utf-8')

print("=== Test 1: dark-knowledge/list (分页) ===")
t0 = time.time()
try:
    req = urllib.request.Request('http://localhost:8001/api/grad-intel/dark-knowledge/list?page=1&per_page=20', headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    elapsed = time.time() - t0
    print(f"  Response: {len(data)} items, {elapsed:.2f}s")
    if data:
        first = data[0]
        print(f"  First: {first.get('title', '')[:50]}")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== Test 2: yanzhao-programs ===")
t0 = time.time()
try:
    req = urllib.request.Request('http://localhost:8001/api/grad-intel/yanzhao-programs?limit=10', headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    elapsed = time.time() - t0
    count = len(data) if isinstance(data, list) else "N/A"
    print(f"  Response: {count} items, {elapsed:.2f}s")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== Test 3: recommend/schools ===")
t0 = time.time()
try:
    req = urllib.request.Request('http://localhost:8001/api/recommend/schools?target_score=370', headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    elapsed = time.time() - t0
    recs = data.get("items", [])
    print(f"  Response: {len(recs)} recommendations, {elapsed:.2f}s")
    if recs:
        r = recs[0]
        print(f"  Top: {r.get('name', '')} ({r.get('match_score', 0)})")
except Exception as e:
    print(f"  ERROR: {e}")

print("\n=== Test 4: recommend/dark-knowledge ===")
t0 = time.time()
try:
    req = urllib.request.Request('http://localhost:8001/api/recommend/dark-knowledge?stage=preparation', headers={"User-Agent": "Mozilla/5.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    elapsed = time.time() - t0
    items = data.get("items", [])
    print(f"  Response: {len(items)} items, {elapsed:.2f}s")
    if items:
        print(f"  First: {items[0].get('title', '')[:50]}")
except Exception as e:
    print(f"  ERROR: {e}")
