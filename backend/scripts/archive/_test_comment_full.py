import urllib.request, json, psycopg2
BASE='http://localhost:8000'
def req(method, path, data=None, token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']=f'Bearer {token}'
    body=json.dumps(data).encode() if data else None
    r=urllib.request.Request(f'{BASE}{path}', data=body, headers=headers, method=method)
    try:
        resp=urllib.request.urlopen(r)
        return json.loads(resp.read()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code

login,_=req('POST','/api/auth/login',{'email':'test2@example.com','password':'testpass123'})
token=login.get('access_token')

conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur=conn.cursor()
cur.execute("SELECT id FROM experience_posts LIMIT 1")
pid=cur.fetchone()[0]
cur.close(); conn.close()
print('EXPERIENCE_POST_ID:', pid)

# Create comment
c,code=req('POST','/api/comments',{'post_id':str(pid),'content':'端到端测试评论','parent_id':None},token)
print('CREATE:', code, 'id=', c.get('id','') if isinstance(c,dict) else c)

# Create reply (nested)
if isinstance(c,dict) and c.get('id'):
    reply,rcode=req('POST','/api/comments',{'post_id':str(pid),'content':'嵌套回复测试','parent_id':c['id']},token)
    print('REPLY:', rcode, 'parent_id=', reply.get('parent_id','') if isinstance(reply,dict) else reply)

# List
c,code=req('GET',f'/api/comments/post/{pid}',token=token)
print('LIST:', code, 'total=', c.get('total',0) if isinstance(c,dict) else c)
