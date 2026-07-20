import urllib.request, json
BASE='http://localhost:8000'
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
H={'Authorization':f'Bearer {token}'}

apis = [
    ('/api/civil-service/post-intel/public', '考公岗位'),
    ('/api/civil-service/dark-knowledge', '考公暗知识'),
    ('/api/salary-benchmarks', '薪资基准'),
    ('/api/companies', '公司列表'),
    ('/api/career-intel/dark-knowledge/list', '就业暗知识'),
    ('/api/grad-intel/dark-knowledge/list', '考研暗知识'),
    ('/api/market-data', '市场数据'),
]
for path, name in apis:
    try:
        req=urllib.request.Request(f'{BASE}{path}',headers=H)
        resp=urllib.request.urlopen(req, timeout=10)
        data=json.loads(resp.read())
        if isinstance(data, dict):
            keys = list(data.keys())[:5]
            items_count = len(data.get('items', []))
            print(f'{name}: dict keys={keys} items={items_count}')
        elif isinstance(data, list):
            print(f'{name}: list[{len(data)}]')
            if data:
                print(f'  first item keys: {list(data[0].keys())[:8]}')
    except Exception as e:
        print(f'{name}: ERR {str(e)[:80]}')
