import urllib.request, json
BASE='http://localhost:8000'

# 登录
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
H={'Authorization':f'Bearer {token}'}

# 考公API
print("=== 考公API ===")
try:
    req=urllib.request.Request(f'{BASE}/api/civil-service/post-intel/public',headers=H)
    resp=urllib.request.urlopen(req, timeout=10)
    data=json.loads(resp.read())
    if isinstance(data, dict):
        print(f"  post-intel/public: {type(data)}, keys={list(data.keys())[:5]}")
        if 'items' in data: print(f"    items数量: {len(data['items'])}")
    elif isinstance(data, list):
        print(f"  post-intel/public: list[{len(data)}]")
except Exception as e:
    print(f"  post-intel/public ERR: {str(e)[:80]}")

try:
    req=urllib.request.Request(f'{BASE}/api/civil-service/dark-knowledge',headers=H)
    resp=urllib.request.urlopen(req, timeout=10)
    data=json.loads(resp.read())
    if isinstance(data, dict):
        print(f"  dark-knowledge: {type(data)}, keys={list(data.keys())[:5]}")
        if 'items' in data: print(f"    items数量: {len(data['items'])}")
    elif isinstance(data, list):
        print(f"  dark-knowledge: list[{len(data)}]")
except Exception as e:
    print(f"  dark-knowledge ERR: {str(e)[:80]}")

# 就业API
print("\n=== 就业API ===")
try:
    req=urllib.request.Request(f'{BASE}/api/salary-benchmarks',headers=H)
    resp=urllib.request.urlopen(req, timeout=10)
    data=json.loads(resp.read())
    if isinstance(data, dict):
        print(f"  salary-benchmarks: {type(data)}, keys={list(data.keys())[:5]}")
        if 'items' in data: print(f"    items数量: {len(data['items'])}")
    elif isinstance(data, list):
        print(f"  salary-benchmarks: list[{len(data)}]")
except Exception as e:
    print(f"  salary-benchmarks ERR: {str(e)[:80]}")

try:
    req=urllib.request.Request(f'{BASE}/api/companies',headers=H)
    resp=urllib.request.urlopen(req, timeout=10)
    data=json.loads(resp.read())
    if isinstance(data, dict):
        print(f"  companies: {type(data)}, keys={list(data.keys())[:5]}")
        if 'items' in data: print(f"    items数量: {len(data['items'])}")
    elif isinstance(data, list):
        print(f"  companies: list[{len(data)}]")
except Exception as e:
    print(f"  companies ERR: {str(e)[:80]}")

try:
    req=urllib.request.Request(f'{BASE}/api/employment/search?keyword=计算机',headers=H)
    resp=urllib.request.urlopen(req, timeout=10)
    data=json.loads(resp.read())
    if isinstance(data, dict):
        print(f"  employment/search: {type(data)}, keys={list(data.keys())[:5]}")
        if 'items' in data: print(f"    items数量: {len(data['items'])}")
    elif isinstance(data, list):
        print(f"  employment/search: list[{len(data)}]")
except Exception as e:
    print(f"  employment/search ERR: {str(e)[:80]}")

# 考研暗知识
print("\n=== 考研暗知识API ===")
try:
    req=urllib.request.Request(f'{BASE}/api/grad-intel/dark-knowledge/list',headers=H)
    resp=urllib.request.urlopen(req, timeout=10)
    data=json.loads(resp.read())
    if isinstance(data, dict):
        print(f"  dark-knowledge/list: {type(data)}, keys={list(data.keys())[:5]}")
        if 'items' in data: print(f"    items数量: {len(data['items'])}")
    elif isinstance(data, list):
        print(f"  dark-knowledge/list: list[{len(data)}]")
except Exception as e:
    print(f"  dark-knowledge/list ERR: {str(e)[:80]}")
