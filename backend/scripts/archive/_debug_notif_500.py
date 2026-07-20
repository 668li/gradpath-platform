import urllib.request, json
BASE='http://localhost:8000'
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
req=urllib.request.Request(f'{BASE}/api/comments',data=json.dumps({'post_id':'015f1da6-aa21-4f75-88b9-e53ff69c7b8d','content':'触发通知测试','parent_id':None}).encode(),headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'},method='POST')
try:
    print(urllib.request.urlopen(req).read().decode()[:300])
except urllib.error.HTTPError as e:
    print('STATUS',e.code)
    print(e.read().decode()[:600])
