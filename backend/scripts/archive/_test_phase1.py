import urllib.request, json
BASE='http://localhost:8000'
# 登录
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
H={'Authorization':f'Bearer {token}','Content-Type':'application/json'}

# 测试events端点
events_body=json.dumps({"events":[{"session_id":"test-sess-001","event_type":"page_view","page":"/dashboard","payload":{"test":True}}]})
req=urllib.request.Request(f'{BASE}/api/events',data=events_body.encode(),headers=H,method='POST')
resp=urllib.request.urlopen(req)
print("POST /api/events:", resp.status, json.loads(resp.read()))

# 测试feedback端点
fb_body=json.dumps({"category":"卡顿","content":"测试反馈","page":"/dashboard","session_id":"test-sess-001"})
req2=urllib.request.Request(f'{BASE}/api/feedback',data=fb_body.encode(),headers=H,method='POST')
resp2=urllib.request.urlopen(req2)
print("POST /api/feedback:", resp2.status, json.loads(resp2.read()))

# 验证表存在
import psycopg2
conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur=conn.cursor()
cur.execute("SELECT count(*) FROM events")
print("events表行数:", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM feedback")
print("feedback表行数:", cur.fetchone()[0])
cur.close(); conn.close()
