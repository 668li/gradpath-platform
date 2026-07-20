import urllib.request, json
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

login=req('POST','/api/auth/login',{'email':'test2@example.com','password':'testpass123'})
token=login[0].get('access_token')
print('LOGIN:', login[1])

# Notifications
n=req('GET','/api/notifications',token=token)
print('NOTIF list:', n[1], 'total=', n[0].get('total',0) if isinstance(n[0],dict) else n)
uc=req('GET','/api/notifications/unread-count',token=token)
print('NOTIF unread:', uc[0].get('unread_count',0) if isinstance(uc[0],dict) else uc)

# Bookmarks
b=req('GET','/api/bookmarks',token=token)
print('BOOKMARK list:', b[1], 'total=', b[0].get('total',0) if isinstance(b[0],dict) else b)
# Add bookmark (target_type=experience_post)
add=req('POST','/api/bookmarks',{'target_type':'experience_post','target_id':'3c225a1e-aa21-4f75-88b9-e53ff69c7b8d'},token)
print('BOOKMARK add:', add[1], 'id=', add[0].get('id','')[:8] if isinstance(add[0],dict) else add)
# List again
b2=req('GET','/api/bookmarks',token=token)
print('BOOKMARK after:', b2[0].get('total',0) if isinstance(b2[0],dict) else b2)
