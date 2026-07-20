import urllib.request, json
BASE='http://localhost:8000'
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
H={'Authorization':f'Bearer {token}'}

tests = [
    ('/api/civil-service/post-intel/public?limit=50', '考公岗位'),
    ('/api/civil-service/dark-knowledge/stages', '考公暗知识阶段'),
    ('/api/career-intel/dark-knowledge/list', '就业暗知识'),
    ('/api/salary-benchmarks', '薪资基准'),
    ('/api/companies', '公司列表'),
    ('/api/employment/stats', '就业统计'),
    ('/api/career-intel/positioning/latest', '求职定位'),
    ('/api/civil-service/positioning/latest', '考公定位'),
]
for path, name in tests:
    try:
        req=urllib.request.Request(f'{BASE}{path}',headers=H)
        resp=urllib.request.urlopen(req, timeout=10)
        data=json.loads(resp.read())
        if isinstance(data, list):
            print(f'{name}: list[{len(data)}]')
            if data:
                print(f'  keys: {list(data[0].keys())[:6]}')
        elif isinstance(data, dict):
            items = data.get('items', [])
            total = data.get('total', '?')
            print(f'{name}: dict total={total} items={len(items)}')
    except Exception as e:
        print(f'{name}: ERR {str(e)[:80]}')
