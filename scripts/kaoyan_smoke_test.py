#!/usr/bin/env python3
"""考研模块核心链路冒烟测试脚本"""
import requests
import json
import sys
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3001"

class SmokeTest:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_id = None
        self.test_results = []
        
    def log_result(self, test_name: str, passed: bool, details: str = ""):
        status = "✓ PASS" if passed else "✗ FAIL"
        self.test_results.append({
            "test": test_name,
            "passed": passed,
            "details": details
        })
        print(f"{status}: {test_name}")
        if details and not passed:
            print(f"  Details: {details}")
    
    def check_service_health(self):
        """检查服务健康状态"""
        try:
            # 后端健康检查
            resp = self.session.get(f"{BASE_URL}/health", timeout=5)
            backend_ok = resp.status_code == 200
            
            # 前端健康检查
            resp = self.session.get(FRONTEND_URL, timeout=5)
            frontend_ok = resp.status_code == 200
            
            self.log_result(
                "服务健康检查",
                backend_ok and frontend_ok,
                f"Backend: {backend_ok}, Frontend: {frontend_ok}"
            )
            return backend_ok and frontend_ok
        except Exception as e:
            self.log_result("服务健康检查", False, str(e))
            return False
    
    def test_auth_register_login(self):
        """测试注册和登录"""
        test_email = f"smoke_test_{int(requests.get('https://www.random.org/integers/?num=1&min=1&max=10000&col=1&base=10&format=plain&rnd=new').text.strip())}@test.com"
        test_password = "Test123456!"
        
        # 注册
        try:
            resp = self.session.post(f"{BASE_URL}/api/auth/register", json={
                "email": test_email,
                "password": test_password,
                "name": "冒烟测试用户"
            }, timeout=10)
            
            if resp.status_code not in [200, 201, 400]:  # 400 可能是邮箱已存在
                self.log_result("用户注册", False, f"Status: {resp.status_code}, Response: {resp.text[:200]}")
                return False
            
            self.log_result("用户注册", True)
        except Exception as e:
            self.log_result("用户注册", False, str(e))
            return False
        
        # 登录
        try:
            resp = self.session.post(f"{BASE_URL}/api/auth/login", json={
                "email": test_email,
                "password": test_password
            }, timeout=10)
            
            if resp.status_code != 200:
                self.log_result("用户登录", False, f"Status: {resp.status_code}")
                return False
            
            data = resp.json()
            self.token = data.get("access_token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            
            self.log_result("用户登录", True)
            return True
        except Exception as e:
            self.log_result("用户登录", False, str(e))
            return False
    
    def test_school_list(self):
        """测试院校列表"""
        try:
            # 尝试获取院校列表（公开接口）
            resp = self.session.get(f"{BASE_URL}/api/grad-intel/intel/public", params={
                "limit": 10
            }, timeout=10)
            
            if resp.status_code != 200:
                self.log_result("院校列表访问", False, f"Status: {resp.status_code}")
                return False
            
            data = resp.json()
            self.log_result("院校列表访问", True, f"获取到 {len(data)} 条记录")
            return True
        except Exception as e:
            self.log_result("院校列表访问", False, str(e))
            return False
    
    def test_school_detail(self):
        """测试院校详情"""
        try:
            # 先获取一个院校名称
            resp = self.session.get(f"{BASE_URL}/api/grad-intel/intel/public", params={
                "limit": 1
            }, timeout=10)
            
            if resp.status_code != 200 or not resp.json():
                self.log_result("院校详情访问", False, "无法获取院校数据")
                return False
            
            school_name = resp.json()[0].get("school_name", "清华大学")
            
            # 获取院校汇总数据
            resp = self.session.get(
                f"{BASE_URL}/api/grad-intel/schools/{school_name}/summary",
                timeout=10
            )
            
            if resp.status_code != 200:
                self.log_result("院校详情访问", False, f"Status: {resp.status_code}")
                return False
            
            self.log_result("院校详情访问", True)
            return True
        except Exception as e:
            self.log_result("院校详情访问", False, str(e))
            return False
    
    def test_mentor_list(self):
        """测试导师列表"""
        try:
            resp = self.session.get(f"{BASE_URL}/api/mentors/kaoyan-mentors", params={
                "page": 1,
                "page_size": 10
            }, timeout=10)
            
            if resp.status_code != 200:
                self.log_result("导师列表访问", False, f"Status: {resp.status_code}")
                return False
            
            data = resp.json()
            total = data.get("total", 0)
            self.log_result("导师列表访问", True, f"共 {total} 位导师")
            return True
        except Exception as e:
            self.log_result("导师列表访问", False, str(e))
            return False
    
    def test_mentor_detail_and_review(self):
        """测试导师详情和评价"""
        try:
            # 获取导师列表
            resp = self.session.get(f"{BASE_URL}/api/mentors/kaoyan-mentors", params={
                "page": 1,
                "page_size": 1
            }, timeout=10)
            
            if resp.status_code != 200 or not resp.json().get("items"):
                self.log_result("导师详情访问", False, "无法获取导师数据")
                return False
            
            mentor_id = resp.json()["items"][0]["id"]
            
            # 获取导师详情
            resp = self.session.get(
                f"{BASE_URL}/api/mentors/kaoyan-mentors/{mentor_id}",
                timeout=10
            )
            
            if resp.status_code != 200:
                self.log_result("导师详情访问", False, f"Status: {resp.status_code}")
                return False
            
            self.log_result("导师详情访问", True)
            
            # 获取导师评价列表
            resp = self.session.get(
                f"{BASE_URL}/api/mentors/kaoyan-mentors/{mentor_id}/reviews",
                params={"page": 1, "page_size": 5},
                timeout=10
            )
            
            if resp.status_code != 200:
                self.log_result("导师评价列表", False, f"Status: {resp.status_code}")
                return False
            
            self.log_result("导师评价列表", True)
            
            # 提交评价
            resp = self.session.post(
                f"{BASE_URL}/api/mentors/kaoyan-mentors/{mentor_id}/reviews",
                json={
                    "rating_academic": 5,
                    "rating_guidance": 5,
                    "rating_relationship": 5,
                    "rating_funding": 5,
                    "rating_workload": 3,
                    "rating_career": 5,
                    "title": "冒烟测试评价",
                    "content": "这是一条用于冒烟测试的评价内容",
                    "pros": ["学术水平高", "指导认真"],
                    "cons": ["工作强度较大"],
                    "is_anonymous": True
                },
                timeout=10
            )
            
            if resp.status_code not in [200, 201]:
                self.log_result("提交导师评价", False, f"Status: {resp.status_code}, Response: {resp.text[:300]}")
                return False
            
            self.log_result("提交导师评价", True)
            return True
        except Exception as e:
            self.log_result("导师详情/评价", False, str(e))
            return False
    
    def test_community_qa(self):
        """测试社区问答"""
        try:
            # 获取问题列表
            resp = self.session.get(f"{BASE_URL}/api/kaoyan/qa", params={
                "page": 1,
                "page_size": 10
            }, timeout=10)
            
            if resp.status_code != 200:
                self.log_result("问答列表访问", False, f"Status: {resp.status_code}")
                return False
            
            data = resp.json()
            self.log_result("问答列表访问", True, f"共 {data.get('total', 0)} 个问题")
            
            # 发布问题
            resp = self.session.post(f"{BASE_URL}/api/kaoyan/qa", json={
                "title": "冒烟测试问题",
                "content": "这是一个用于冒烟测试的问题内容",
                "tags": ["测试", "冒烟测试"]
            }, timeout=10)
            
            if resp.status_code not in [200, 201]:
                self.log_result("发布问题", False, f"Status: {resp.status_code}")
                return False
            
            question_id = resp.json().get("id")
            self.log_result("发布问题", True)
            
            # 回答问题
            if question_id:
                resp = self.session.post(
                    f"{BASE_URL}/api/kaoyan/qa/{question_id}/answers",
                    json={
                        "content": "这是对这个问题的回答 - 冒烟测试"
                    },
                    timeout=10
                )
                
                if resp.status_code not in [200, 201]:
                    self.log_result("回答问题", False, f"Status: {resp.status_code}")
                    return False
                
                self.log_result("回答问题", True)
            
            return True
        except Exception as e:
            self.log_result("社区问答", False, str(e))
            return False
    
    def test_community_posts(self):
        """测试社区经验贴"""
        try:
            # 获取经验贴列表
            resp = self.session.get(f"{BASE_URL}/api/kaoyan/experience-posts", params={
                "page": 1,
                "page_size": 10
            }, timeout=10)
            
            if resp.status_code != 200:
                self.log_result("经验贴列表访问", False, f"Status: {resp.status_code}")
                return False
            
            data = resp.json()
            self.log_result("经验贴列表访问", True, f"共 {data.get('total', 0)} 篇帖子")
            
            # 发布经验贴
            resp = self.session.post(f"{BASE_URL}/api/kaoyan/experience-posts", json={
                "title": "冒烟测试经验贴",
                "content": "这是一篇用于冒烟测试的经验贴内容，包含一些测试文字。",
                "category": "备考经验",
                "tags": ["测试", "冒烟测试"]
            }, timeout=10)
            
            if resp.status_code not in [200, 201]:
                self.log_result("发布经验贴", False, f"Status: {resp.status_code}")
                return False
            
            self.log_result("发布经验贴", True)
            return True
        except Exception as e:
            self.log_result("社区经验贴", False, str(e))
            return False
    
    def test_dark_knowledge(self):
        """测试暗知识功能"""
        try:
            # 获取暗知识阶段列表
            resp = self.session.get(f"{BASE_URL}/api/grad-intel/dark-knowledge/stages", timeout=10)
            
            if resp.status_code != 200:
                self.log_result("暗知识阶段列表", False, f"Status: {resp.status_code}")
                return False
            
            stages = resp.json()
            self.log_result("暗知识阶段列表", True, f"共 {len(stages)} 个阶段")
            
            # 获取暗知识内容
            resp = self.session.get(f"{BASE_URL}/api/grad-intel/dark-knowledge/list", timeout=10)
            
            if resp.status_code != 200:
                self.log_result("暗知识内容访问", False, f"Status: {resp.status_code}")
                return False
            
            data = resp.json()
            self.log_result("暗知识内容访问", True, f"获取到 {len(data)} 条内容")
            return True
        except Exception as e:
            self.log_result("暗知识功能", False, str(e))
            return False
    
    def test_frontend_pages(self):
        """测试前端页面可访问性"""
        pages = [
            ("/kaoyan", "考研首页"),
            ("/kaoyan/schools", "院校列表"),
            ("/kaoyan/mentors", "导师列表"),
            ("/kaoyan/community", "社区首页"),
            ("/kaoyan/community/qa", "问答社区"),
            ("/kaoyan/community/posts", "经验贴"),
            ("/kaoyan/strategy", "备考策略"),
        ]
        
        all_passed = True
        for path, name in pages:
            try:
                resp = self.session.get(f"{FRONTEND_URL}{path}", timeout=10)
                if resp.status_code != 200:
                    self.log_result(f"前端页面 - {name}", False, f"Status: {resp.status_code}")
                    all_passed = False
                else:
                    self.log_result(f"前端页面 - {name}", True)
            except Exception as e:
                self.log_result(f"前端页面 - {name}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("考研模块核心链路冒烟测试")
        print("=" * 60)
        print()
        
        # 1. 服务健康检查
        print("【步骤 1】服务健康检查")
        if not self.check_service_health():
            print("\n服务未启动，测试终止")
            return False
        print()
        
        # 2. 注册/登录
        print("【步骤 2】用户认证")
        if not self.test_auth_register_login():
            print("\n认证失败，测试终止")
            return False
        print()
        
        # 3. 院校列表
        print("【步骤 3】院校列表")
        self.test_school_list()
        print()
        
        # 4. 院校详情
        print("【步骤 4】院校详情")
        self.test_school_detail()
        print()
        
        # 5. 导师列表
        print("【步骤 5】导师列表")
        self.test_mentor_list()
        print()
        
        # 6. 导师详情和评价
        print("【步骤 6】导师详情和评价")
        self.test_mentor_detail_and_review()
        print()
        
        # 7. 社区问答
        print("【步骤 7】社区问答")
        self.test_community_qa()
        print()
        
        # 8. 社区经验贴
        print("【步骤 8】社区经验贴")
        self.test_community_posts()
        print()
        
        # 9. 暗知识
        print("【步骤 9】暗知识功能")
        self.test_dark_knowledge()
        print()
        
        # 10. 前端页面
        print("【步骤 10】前端页面可访问性")
        self.test_frontend_pages()
        print()
        
        # 汇总结果
        print("=" * 60)
        print("测试结果汇总")
        print("=" * 60)
        passed = sum(1 for r in self.test_results if r["passed"])
        total = len(self.test_results)
        print(f"通过: {passed}/{total}")
        print(f"通过率: {passed/total*100:.1f}%")
        print()
        
        if passed == total:
            print("✓ 所有测试通过！")
            return True
        else:
            print("✗ 部分测试失败:")
            for r in self.test_results:
                if not r["passed"]:
                    print(f"  - {r['test']}: {r['details']}")
            return False

if __name__ == "__main__":
    tester = SmokeTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
