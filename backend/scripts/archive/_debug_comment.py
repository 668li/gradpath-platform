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

login,code=req('POST','/api/auth/login',{'email':'test2@example.com','password':'testpass123'})
token=login.get('access_token')

# 看comments.py的schema定义和post_id类型
import subprocess
print("=== comments.py schema ===")
print(subprocess.run(['cat','/app/app/api/comments.py'],capture_output=True,text=True).stdout[:1500])
