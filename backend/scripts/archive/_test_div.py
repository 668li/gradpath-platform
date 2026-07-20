import urllib.request, json
BASE='http://localhost:8000'
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
req=urllib.request.Request(f'{BASE}/api/learning-methods/recommend?limit=5',headers={'Authorization':f'Bearer {token}'})
data=json.loads(urllib.request.urlopen(req).read())
print("推荐结果:", len(data), "条")
tags_seen = {}
for i, item in enumerate(data):
    ts = item.get('tags',[])
    for t in ts: tags_seen[t] = tags_seen.get(t,0)+1
    print(f"{i+1}. {item.get('title','')[:35]} | tags: {ts}")
print("\nTag分布:", tags_seen)
print("多样性:", len(tags_seen), "种不同tag")
