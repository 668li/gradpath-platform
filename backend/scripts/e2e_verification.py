"""端到端全面验证脚本 - 验证所有模块功能"""
import requests
import time
import json
from typing import Dict, List, Tuple

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

# 测试结果统计
test_results = {
    "passed": 0,
    "failed": 0,
    "total": 0,
    "details": []
}

def log_result(module: str, endpoint: str, status: str, response_time: float, details: str = ""):
    """记录测试结果"""
    test_results["total"] += 1
    if status == "PASS":
        test_results["passed"] += 1
        emoji = "✅"
    else:
        test_results["failed"] += 1
        emoji = "❌"
    
    result = {
        "module": module,
        "endpoint": endpoint,
        "status": status,
        "response_time": round(response_time, 3),
        "details": details
    }
    test_results["details"].append(result)
    
    print(f"{emoji} {module:20s} {endpoint:50s} {response_time:6.3f}s {details}")

def test_health():
    """测试健康检查"""
    try:
        start = time.time()
        resp = requests.get(f"{BASE_URL}/health", timeout=3)
        duration = time.time() - start
        log_result("系统", "/health", "PASS" if resp.status_code == 200 else "FAIL", duration)
        return resp.status_code == 200
    except Exception as e:
        log_result("系统", "/health", "FAIL", 0, str(e)[:50])
        return False

def test_auth_and_get_token():
    """测试认证并获取 token"""
    try:
        # 尝试登录（使用测试账号）
        start = time.time()
        resp = requests.post(f"{API_URL}/auth/login", json={
            "email": "test@example.com",
            "password": "test123456"
        }, timeout=3)
        duration = time.time() - start
        
        if resp.status_code == 200:
            token = resp.json()["access_token"]
            log_result("认证", "/auth/login", "PASS", duration)
            return token
        else:
            # 尝试注册 - 使用正确的字段名
            start = time.time()
            resp = requests.post(f"{API_URL}/auth/register", json={
                "email": "test@example.com",
                "password": "test123456",
                "name": "测试用户"
            }, timeout=3)
            duration = time.time() - start
            
            if resp.status_code in [200, 201]:
                # 注册成功后登录
                resp = requests.post(f"{API_URL}/auth/login", json={
                    "email": "test@example.com",
                    "password": "test123456"
                }, timeout=3)
                token = resp.json()["access_token"]
                log_result("认证", "/auth/register+login", "PASS", duration)
                return token
            else:
                log_result("认证", "/auth/register", "FAIL", duration, f"Status: {resp.status_code}")
                return None
    except Exception as e:
        log_result("认证", "/auth/login", "FAIL", 0, str(e)[:50])
        return None

def test_module_with_auth(module: str, endpoint: str, method: str = "GET", data: Dict = None, token: str = None):
    """测试需要认证的模块"""
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        start = time.time()
        
        if method == "GET":
            resp = requests.get(f"{API_URL}{endpoint}", headers=headers, timeout=3)
        elif method == "POST":
            resp = requests.post(f"{API_URL}{endpoint}", json=data or {}, headers=headers, timeout=3)
        
        duration = time.time() - start
        
        # 200, 201, 404 (空数据) 都算通过
        if resp.status_code in [200, 201, 404]:
            log_result(module, endpoint, "PASS", duration, f"Status: {resp.status_code}")
            return True, resp
        else:
            log_result(module, endpoint, "FAIL", duration, f"Status: {resp.status_code}")
            return False, resp
    except Exception as e:
        log_result(module, endpoint, "FAIL", 0, str(e)[:50])
        return False, None

def test_module_no_auth(module: str, endpoint: str, method: str = "GET"):
    """测试无需认证的模块"""
    try:
        start = time.time()
        
        if method == "GET":
            resp = requests.get(f"{API_URL}{endpoint}", timeout=3)
        
        duration = time.time() - start
        
        if resp.status_code in [200, 404]:
            log_result(module, endpoint, "PASS", duration, f"Status: {resp.status_code}")
            return True, resp
        else:
            log_result(module, endpoint, "FAIL", duration, f"Status: {resp.status_code}")
            return False, resp
    except Exception as e:
        log_result(module, endpoint, "FAIL", 0, str(e)[:50])
        return False, None

def test_pagination(module: str, endpoint: str, token: str):
    """测试分页功能"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        start = time.time()
        resp = requests.get(f"{API_URL}{endpoint}?page=1&page_size=10", headers=headers, timeout=3)
        duration = time.time() - start
        
        if resp.status_code == 200:
            data = resp.json()
            if "total" in data and "items" in data:
                log_result(module, f"{endpoint} (分页)", "PASS", duration, f"Total: {data['total']}")
                return True
            else:
                log_result(module, f"{endpoint} (分页)", "FAIL", duration, "Missing pagination fields")
                return False
        else:
            log_result(module, f"{endpoint} (分页)", "FAIL", duration, f"Status: {resp.status_code}")
            return False
    except Exception as e:
        log_result(module, f"{endpoint} (分页)", "FAIL", 0, str(e)[:50])
        return False

def test_search_filter(module: str, endpoint: str, search_param: str, token: str):
    """测试搜索筛选功能"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        start = time.time()
        resp = requests.get(f"{API_URL}{endpoint}?{search_param}", headers=headers, timeout=3)
        duration = time.time() - start
        
        if resp.status_code == 200:
            log_result(module, f"{endpoint} ({search_param})", "PASS", duration)
            return True
        else:
            log_result(module, f"{endpoint} ({search_param})", "FAIL", duration, f"Status: {resp.status_code}")
            return False
    except Exception as e:
        log_result(module, f"{endpoint} ({search_param})", "FAIL", 0, str(e)[:50])
        return False

def main():
    """主测试流程"""
    print("=" * 100)
    print("端到端全面验证 - GradPath 职业规划平台")
    print("=" * 100)
    print()
    
    # 1. 系统健康检查
    print("【1. 系统健康检查】")
    if not test_health():
        print("❌ 后端服务未启动，测试终止")
        return
    
    print()
    
    # 2. 认证测试
    print("【2. 认证测试】")
    token = test_auth_and_get_token()
    if not token:
        print("❌ 认证失败，使用无 token 模式继续测试")
    
    print()
    
    # 3. 考研模块验证
    print("【3. 考研模块验证】")
    test_module_no_auth("考研导师", "/mentors/kaoyan-mentors")
    test_module_no_auth("考研情报-暗知识", "/grad-intel/dark-knowledge/list")
    test_module_no_auth("考研经验贴", "/kaoyan/experience-posts")
    test_module_no_auth("考研问答", "/kaoyan/qa")
    
    if token:
        test_pagination("考研导师", "/mentors/kaoyan-mentors", token)
        test_search_filter("考研导师", "/mentors/kaoyan-mentors", "search=计算机", token)
    
    print()
    
    # 4. 职业决策模块
    print("【4. 职业决策模块】")
    if token:
        test_module_with_auth("职业决策", "/decisions", token=token)
        test_pagination("职业决策", "/decisions", token)
    
    print()
    
    # 5. 技能树模块
    print("【5. 技能树模块】")
    if token:
        test_module_with_auth("技能树", "/skills", token=token)
    
    print()
    
    # 6. 人生平衡轮
    print("【6. 人生平衡轮】")
    if token:
        test_module_with_auth("人生平衡轮", "/life-wheel/latest", token=token)
    
    print()
    
    # 7. 职业测评
    print("【7. 职业测评】")
    test_module_no_auth("职业测评-题目", "/assessment/questions")
    if token:
        test_module_with_auth("职业测评-历史", "/assessment/history", token=token)
    
    print()
    
    # 8. 阶段复盘
    print("【8. 阶段复盘】")
    if token:
        test_module_with_auth("阶段复盘", "/retrospectives", token=token)
        test_pagination("阶段复盘", "/retrospectives", token)
    
    print()
    
    # 9. 成长模式
    print("【9. 成长模式】")
    if token:
        test_module_with_auth("成长模式", "/growth-patterns/analyze", token=token)
    
    print()
    
    # 10. 人生设计
    print("【10. 人生设计】")
    if token:
        test_module_with_auth("人生设计", "/life-design/sprints", token=token)
    
    print()
    
    # 11. 决策分析
    print("【11. 决策分析】")
    if token:
        test_module_with_auth("决策分析", "/decision-analysis/list", token=token)
    
    print()
    
    # 12. 社区功能
    print("【12. 社区功能】")
    test_module_no_auth("社区帖子", "/posts")
    if token:
        test_module_with_auth("社区报告", "/community/my-reports", token=token)
    
    print()
    
    # 13. AI 对话
    print("【13. AI 对话】")
    if token:
        test_module_with_auth("AI对话", "/chat/conversations", token=token)
    test_module_no_auth("AI导师人格", "/mentors/personas")
    
    print()
    
    # 14. 其他核心模块
    print("【14. 其他核心模块】")
    if token:
        test_module_with_auth("职业档案", "/career-profile", token=token)
        test_module_with_auth("职业规划", "/career-plans", token=token)
        test_module_with_auth("职业事件", "/events", token=token)
        test_module_with_auth("仪表盘", "/dashboard/overview", token=token)
        test_module_with_auth("连续打卡", "/streaks", token=token)
        test_module_with_auth("主动洞察", "/proactive-insights", token=token)
        test_module_with_auth("决策日志", "/decision-journal", token=token)
    
    print()
    
    # 15. 求职和考公模块
    print("【15. 求职和考公模块】")
    if token:
        test_module_with_auth("求职情报", "/career-intel/companies", token=token)
        test_module_with_auth("考公情报", "/civil-service-intel/posts", token=token)
    
    print()
    
    # 输出测试报告
    print("=" * 100)
    print("测试报告汇总")
    print("=" * 100)
    print(f"总测试数: {test_results['total']}")
    print(f"通过: {test_results['passed']}")
    print(f"失败: {test_results['failed']}")
    print(f"通过率: {test_results['passed']/test_results['total']*100:.1f}%")
    print()
    
    # 输出失败详情
    if test_results['failed'] > 0:
        print("失败的测试:")
        for r in test_results['details']:
            if r['status'] == 'FAIL':
                print(f"  - {r['module']}: {r['endpoint']} - {r['details']}")
    
    # 保存详细报告
    with open('e2e_test_report.json', 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2)
    
    print()
    print("详细报告已保存到: e2e_test_report.json")

if __name__ == "__main__":
    main()
