"""API 性能测试脚本 - 验证响应时间和性能指标"""
import requests
import time
import json
from typing import Dict, List

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api"

# 性能测试结果
performance_results = {
    "tests": [],
    "avg_response_time": 0,
    "max_response_time": 0,
    "min_response_time": 0,
    "tests_over_3s": 0,
    "total_tests": 0
}

def test_endpoint_performance(module: str, endpoint: str, method: str = "GET", 
                              data: Dict = None, token: str = None, 
                              expected_max_time: float = 3.0):
    """测试单个端点的性能"""
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        
        start = time.time()
        if method == "GET":
            resp = requests.get(f"{API_URL}{endpoint}", headers=headers, timeout=10)
        elif method == "POST":
            resp = requests.post(f"{API_URL}{endpoint}", json=data or {}, 
                               headers=headers, timeout=10)
        
        duration = time.time() - start
        
        result = {
            "module": module,
            "endpoint": endpoint,
            "method": method,
            "status_code": resp.status_code,
            "response_time": round(duration, 3),
            "within_limit": duration <= expected_max_time,
            "data_size": len(resp.content) if resp.status_code == 200 else 0
        }
        
        performance_results["tests"].append(result)
        performance_results["total_tests"] += 1
        
        if duration > expected_max_time:
            performance_results["tests_over_3s"] += 1
        
        status = "✅" if duration <= expected_max_time else "⚠️"
        print(f"{status} {module:20s} {endpoint:50s} {duration:6.3f}s "
              f"(Status: {resp.status_code}, Size: {len(resp.content)} bytes)")
        
        return result
    except Exception as e:
        print(f"❌ {module:20s} {endpoint:50s} ERROR: {str(e)[:50]}")
        return None

def get_auth_token():
    """获取认证 token"""
    try:
        resp = requests.post(f"{API_URL}/auth/login", json={
            "email": "test@example.com",
            "password": "test123456"
        }, timeout=3)
        if resp.status_code == 200:
            return resp.json()["access_token"]
    except:
        pass
    return None

def main():
    """主测试流程"""
    print("=" * 120)
    print("API 性能测试 - GradPath 职业规划平台")
    print("=" * 120)
    print()
    
    # 获取认证 token
    token = get_auth_token()
    if not token:
        print("⚠️  无法获取认证 token，部分测试将跳过")
    
    print()
    
    # 1. 系统端点
    print("【1. 系统端点】")
    test_endpoint_performance("系统", "/health")
    test_endpoint_performance("系统", "/ready")
    print()
    
    # 2. 考研模块（无需认证）
    print("【2. 考研模块】")
    test_endpoint_performance("考研导师", "/mentors/kaoyan-mentors")
    test_endpoint_performance("考研导师", "/mentors/kaoyan-mentors?page=1&page_size=50")
    test_endpoint_performance("考研导师", "/mentors/kaoyan-mentors?search=计算机")
    test_endpoint_performance("考研导师", "/mentors/kaoyan-mentors?university=清华大学")
    test_endpoint_performance("考研情报", "/grad-intel/dark-knowledge/list")
    test_endpoint_performance("考研经验贴", "/kaoyan/experience-posts")
    test_endpoint_performance("考研问答", "/kaoyan/qa")
    print()
    
    # 3. 职业测评（无需认证）
    print("【3. 职业测评】")
    test_endpoint_performance("职业测评", "/assessment/questions")
    test_endpoint_performance("职业测评", "/assessment/questions?type=mbti")
    print()
    
    # 4. AI 导师（无需认证）
    print("【4. AI 导师】")
    test_endpoint_performance("AI导师", "/mentors/personas")
    print()
    
    # 5. 需要认证的模块
    if token:
        print("【5. 职业决策模块】")
        test_endpoint_performance("职业决策", "/decisions", token=token)
        test_endpoint_performance("职业决策", "/decisions?page=1&page_size=20", token=token)
        print()
        
        print("【6. 技能树模块】")
        test_endpoint_performance("技能树", "/skills", token=token)
        print()
        
        print("【7. 人生平衡轮】")
        test_endpoint_performance("人生平衡轮", "/life-wheel/latest", token=token)
        print()
        
        print("【8. 阶段复盘】")
        test_endpoint_performance("阶段复盘", "/retrospectives", token=token)
        test_endpoint_performance("阶段复盘", "/retrospectives?page=1&page_size=10", token=token)
        print()
        
        print("【9. 成长模式】")
        test_endpoint_performance("成长模式", "/growth-patterns/analyze", token=token)
        print()
        
        print("【10. 人生设计】")
        test_endpoint_performance("人生设计", "/life-design/sprints", token=token)
        print()
        
        print("【11. 决策分析】")
        test_endpoint_performance("决策分析", "/decision-analysis/list", token=token)
        print()
        
        print("【12. 社区功能】")
        test_endpoint_performance("社区报告", "/community/my-reports", token=token)
        test_endpoint_performance("社区报告", "/community/my-reports?page=1&page_size=10", token=token)
        print()
        
        print("【13. AI 对话】")
        test_endpoint_performance("AI对话", "/chat/conversations", token=token)
        print()
        
        print("【14. 其他核心模块】")
        test_endpoint_performance("职业档案", "/career-profile", token=token)
        test_endpoint_performance("职业规划", "/career-plans", token=token)
        test_endpoint_performance("职业事件", "/events", token=token)
        test_endpoint_performance("仪表盘", "/dashboard/overview", token=token)
        test_endpoint_performance("连续打卡", "/streaks", token=token)
        test_endpoint_performance("主动洞察", "/proactive-insights", token=token)
        test_endpoint_performance("决策日志", "/decision-journal", token=token)
        print()
        
        print("【15. 求职和考公模块】")
        test_endpoint_performance("求职情报", "/career-intel/companies", token=token)
        test_endpoint_performance("考公情报", "/civil-service-intel/posts", token=token)
        print()
    
    # 计算统计信息
    if performance_results["tests"]:
        response_times = [t["response_time"] for t in performance_results["tests"] if t]
        performance_results["avg_response_time"] = round(sum(response_times) / len(response_times), 3)
        performance_results["max_response_time"] = round(max(response_times), 3)
        performance_results["min_response_time"] = round(min(response_times), 3)
    
    # 输出性能报告
    print("=" * 120)
    print("API 性能测试报告")
    print("=" * 120)
    print(f"总测试数: {performance_results['total_tests']}")
    print(f"平均响应时间: {performance_results['avg_response_time']}s")
    print(f"最大响应时间: {performance_results['max_response_time']}s")
    print(f"最小响应时间: {performance_results['min_response_time']}s")
    print(f"超过 3s 的测试: {performance_results['tests_over_3s']}")
    print(f"性能达标率: {(performance_results['total_tests'] - performance_results['tests_over_3s']) / performance_results['total_tests'] * 100:.1f}%")
    print()
    
    # 输出慢速端点
    slow_endpoints = [t for t in performance_results["tests"] if t and t["response_time"] > 2.0]
    if slow_endpoints:
        print("响应时间超过 2s 的端点:")
        for ep in slow_endpoints:
            print(f"  - {ep['module']}: {ep['endpoint']} - {ep['response_time']}s")
    else:
        print("✅ 所有端点响应时间均在 2s 以内")
    
    # 保存报告
    with open('api_performance_report.json', 'w', encoding='utf-8') as f:
        json.dump(performance_results, f, ensure_ascii=False, indent=2)
    
    print()
    print("详细报告已保存到: api_performance_report.json")

if __name__ == "__main__":
    main()
