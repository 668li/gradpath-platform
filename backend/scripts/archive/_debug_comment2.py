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

# 看schema CommentCreate定义
import subprocess
schema=subprocess.run(['cat','/app/app/schemas/comment.py'],capture_output=True,text=True).stdout
print("=== CommentCreate schema ===")
print(schema[:1000])

# 看CommentCreate需要哪些字段 - 直接试带user_id
conn=psycopg2.connect("postgresql://gradpath:changeme@db:5432/gradpath")
cur=conn.cursor()
cur.execute("SELECT id FROM posts LIMIT 1")
pid=cur.fetchone()[0]
cur.close(); conn.close()

# 试不同参数组合
for payload in [
    {'post_id':str(pid),'content':'测试','parent_id':None},
    {'post_id':str(pid),'content':'测试'},
    {'content':'测试','post_id':str(pid),'parent_id':None},
]:
    c,code=req('POST','/api/comments',payload,token)
    print(f'payload={payload} -> {code}: {str(c)[:150]}')
