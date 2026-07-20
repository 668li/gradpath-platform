import urllib.request, json, psycopg2
BASE='http://localhost:8000'
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur=conn.cursor()
cur.execute("SELECT id FROM experience_posts WHERE user_id != (SELECT id FROM users WHERE email='test2@example.com') LIMIT 1")
pid=str(cur.fetchone()[0])
cur.close(); conn.close()
print('Full PID:', pid)
req=urllib.request.Request(f'{BASE}/api/comments',data=json.dumps({'post_id':pid,'content':'触发通知测试评论','parent_id':None}).encode(),headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'},method='POST')
try:
    r=urllib.request.urlopen(req).read().decode()
    print('COMMENT 201:', r[:120])
    # check notifications for the post author via DB directly
    conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
    cur=conn.cursor()
    cur.execute("SELECT count(*) FROM notifications WHERE link=%s", (f'/kaoyan/community/posts/{pid}',))
    print('Notifications for this post:', cur.fetchone()[0])
    cur.close(); conn.close()
except urllib.error.HTTPError as e:
    print('STATUS',e.code, e.read().decode()[:400])
