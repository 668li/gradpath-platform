import urllib.request, json
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

# Login
login,code=req('POST','/api/auth/login',{'email':'test2@example.com','password':'testpass123'})
token=login.get('access_token')
print('LOGIN:', code, 'token_len=', len(token) if token else 0)

# Get a post from DB
import psycopg2
conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur=conn.cursor()
cur.execute("SELECT id FROM posts LIMIT 1")
pid=cur.fetchone()[0]
cur.close(); conn.close()
print('POST_ID:', pid)

# Create comment
c,code=req('POST','/api/comments',{'post_id':str(pid),'content':'端到端测试评论','parent_id':None}, token)
print('CREATE COMMENT:', code, 'id=', c.get('id','') if isinstance(c,dict) else c)

# Get comments list
c,code=req('GET',f'/api/comments/post/{pid}', token=token)
print('LIST COMMENTS:', code, 'total=', c.get('total',0) if isinstance(c,dict) else c)
