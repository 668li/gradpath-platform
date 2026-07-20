import urllib.request, json
BASE='http://localhost:8000'
def req(method, path, data=None, token=None, raw=False):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']=f'Bearer {token}'
    body=json.dumps(data).encode() if data else None
    r=urllib.request.Request(f'{BASE}{path}', data=body, headers=headers, method=method)
    try:
        resp=urllib.request.urlopen(r)
        ctype=resp.headers.get('Content-Type','')
        if raw or 'application/pdf' in ctype:
            return resp.read(), resp.status, ctype
        return json.loads(resp.read()), resp.status, ctype
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode()), e.code, ''
        except:
            return e.read().decode(), e.code, ''

login=req('POST','/api/auth/login',{'email':'test2@example.com','password':'testpass123'})
token=login[0].get('access_token')

print("=== PDF导出 (export_v2) ===")
for ep in ['/api/export-v2/school-report', '/api/export-v2/career-report', '/api/export-v2/profile-report']:
    body,code,ctype=req('GET',ep,token=token,raw=True)
    size=len(body) if isinstance(body,bytes) else 0
    print(f'{ep} -> {code} ctype={ctype} size={size}')

print("=== 管理仪表盘 (dashboard) ===")
for ep in ['/api/dashboard/overview', '/api/dashboard/weekly-recap']:
    d=req('GET',ep,token=token)
    if isinstance(d[0],dict):
        keys=list(d[0].keys())[:5]
        print(f'{ep} -> {d[1]} keys={keys}')
    else:
        print(f'{ep} -> {d[1]} {str(d[0])[:100]}')
