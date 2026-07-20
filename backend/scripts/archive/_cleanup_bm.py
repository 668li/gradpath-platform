import urllib.request, json
BASE='http://localhost:8000'
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
req=urllib.request.Request(f'{BASE}/api/bookmarks?target_type=post',headers={'Authorization':f'Bearer {token}'})
data=json.loads(urllib.request.urlopen(req).read())
for b in data.get('items', []):
    d=urllib.request.Request(f'{BASE}/api/bookmarks/{b["id"]}',headers={'Authorization':f'Bearer {token}'},method='DELETE')
    urllib.request.urlopen(d)
    print('deleted', b['id'][:8])
print('cleanup done, remaining:', len(data.get('items', [])))
