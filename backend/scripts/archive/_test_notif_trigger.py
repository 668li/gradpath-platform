import urllib.request, json, psycopg2
BASE='http://localhost:8000'
def req(method, path, data=None, token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']=f'Bearer {token}'
    body=json.dumps(data).encode() if data else None
    r=urllib.request.Request(f'{BASE}{path}', data=body, headers=headers, method=method)
    try:
        resp=urllib.request.urlopen(r)
        ctype=resp.headers.get('Content-Type','')
        if 'application/json' in ctype: return json.loads(resp.read()), resp.status
        return resp.read(), resp.status
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()), e.code
        except: return e.read().decode(), e.code

# Login as test2
login=req('POST','/api/auth/login',{'email':'test2@example.com','password':'testpass123'})
token=login[0].get('access_token')

# Find a post NOT owned by test2 (so notification fires)
conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur=conn.cursor()
cur.execute("SELECT id, user_id, title FROM experience_posts WHERE user_id != (SELECT id FROM users WHERE email='test2@example.com') LIMIT 1")
row=cur.fetchone()
cur.close(); conn.close()
pid, owner_id, title = row
print('Post:', str(pid)[:8], 'owner:', str(owner_id)[:8], 'title:', title[:30])

# Create comment as test2
c=req('POST','/api/comments',{'post_id':str(pid),'content':'测试触发通知的评论','parent_id':None},token)
print('COMMENT:', c[1], 'id=', str(c[0].get('id',''))[:8] if isinstance(c[0],dict) else c)

# Now login as the post owner to check notifications
# We need owner's email - get it
conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur=conn.cursor()
cur.execute("SELECT email FROM users WHERE id=%s", (owner_id,))
owner_email=cur.fetchone()[0]
cur.close(); conn.close()
print('Owner email:', owner_email)

owner_login=req('POST','/api/auth/login',{'email':owner_email,'password':'testpass123'})
owner_token=owner_login[0].get('access_token') if owner_login[1]==200 else None
if owner_token:
    n=req('GET','/api/notifications/unread-count',token=owner_token)
    print('Owner unread notifications:', n[0].get('unread_count',0) if isinstance(n[0],dict) else n)
else:
    print('Could not login as owner (maybe wrong password for seed user)')
