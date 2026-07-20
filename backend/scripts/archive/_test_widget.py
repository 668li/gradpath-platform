import urllib.request, json
BASE='http://localhost:4001'
# 测试浮窗是否在测试模式渲染（检查HTML中是否包含反馈相关文本）
try:
    html = urllib.request.urlopen(f'{BASE}/').read().decode('utf-8', errors='ignore')
    has_fab = '反馈问题' in html or 'MessageSquareWarning' in html
    print(f"首页HTML包含反馈浮窗: {has_fab}")
    # 检查 NEXT_PUBLIC_TEST_MODE 是否注入
    has_test_env = 'NEXT_PUBLIC_TEST_MODE' in html
    print(f"测试模式env注入: {has_test_env}")
except Exception as e:
    print(f"前端访问失败: {e}")

# 测试feedback API直接提交
BASE_API='http://localhost:8000'
login=json.loads(urllib.request.urlopen(urllib.request.Request(f'{BASE_API}/api/auth/login',data=json.dumps({'email':'test2@example.com','password':'testpass123'}).encode(),headers={'Content-Type':'application/json'})).read())
token=login.get('access_token')
H={'Authorization':f'Bearer {token}','Content-Type':'application/json'}
fb_body=json.dumps({"category":"找不到入口","content":"测试浮窗提交","page":"/dashboard","session_id":"widget-test"})
req=urllib.request.Request(f'{BASE_API}/api/feedback',data=fb_body.encode(),headers=H,method='POST')
resp=urllib.request.urlopen(req)
print(f"浮窗提交反馈: {resp.status}", json.loads(resp.read()))
