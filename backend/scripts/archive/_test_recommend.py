import urllib.request, json
BASE='http://localhost:8000'
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
req=urllib.request.Request(f'{BASE}/api/learning-methods/recommend?limit=3',headers={'Authorization':f'Bearer {token}'})
data=json.loads(urllib.request.urlopen(req).read())
print("推荐结果:", len(data), "条")
for item in data:
    print(f"  - {item.get('title','')[:50]}")
    print(f"    reason: {item.get('reason','无')[:80]}")
    print(f"    tags: {item.get('tags',[])}")
    print()
