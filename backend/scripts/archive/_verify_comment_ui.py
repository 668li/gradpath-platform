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
        if 'application/json' in ctype:
            return json.loads(resp.read()), resp.status
        return resp.read(), resp.status
    except urllib.error.HTTPError as e:
        try: return json.loads(e.read().decode()), e.code
        except: return e.read().decode(), e.code

# Login
login=req('POST','/api/auth/login',{'email':'test2@example.com','password':'testpass123'})
token=login[0].get('access_token')
print('LOGIN:', login[1])

# Get an experience post
conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur=conn.cursor()
cur.execute("SELECT id FROM experience_posts LIMIT 1")
pid=cur.fetchone()[0]
cur.close(); conn.close()
print('POST:', str(pid)[:8])

# Before count
before=req('GET',f'/api/comments/post/{pid}',token=token)
print('BEFORE total:', before[0].get('total',0) if isinstance(before[0],dict) else before)

# Create comment
c=req('POST','/api/comments',{'post_id':str(pid),'content':'前端接入测试评论','parent_id':None},token)
cid=c[0].get('id') if isinstance(c[0],dict) else None
print('CREATE:', c[1], 'cid=', str(cid)[:8] if cid else 'FAIL')

# Create reply
if cid:
    r=req('POST','/api/comments',{'post_id':str(pid),'content':'前端接入嵌套回复','parent_id':cid},token)
    print('REPLY:', r[1])

# After count
after=req('GET',f'/api/comments/post/{pid}',token=token)
print('AFTER total:', after[0].get('total',0) if isinstance(after[0],dict) else after)
