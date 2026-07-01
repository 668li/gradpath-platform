# backend/tests/test_career_plans.py
"""职业规划 API 测试 — Phase 11。"""
import uuid

from app.models.career_plan import CareerPlan
from app.models.user import User


def _seed_plan(db_session, user_id, milestones=None):
    """预置一条职业规划。"""
    if milestones is None:
        milestones = [
            {"title": "掌握Go基础", "description": "学习Go语法", "deadline": "2025-03-01", "skills": ["Go"], "status": "pending"},
            {"title": "刷算法题", "description": "LeetCode 200道", "deadline": "2025-05-01", "skills": ["算法"], "status": "pending"},
        ]
    plan = CareerPlan(
        user_id=user_id,
        goal_text="6个月内进入字节跳动后端开发岗",
        current_state={"skills": "Python基础"},
        target_state={"position": "后端开发", "company": "字节跳动"},
        gaps=[{"skill": "Go语言", "current_level": 1, "target_level": 4, "gap": "需系统学习"}],
        milestones=milestones,
        timeline_months=6,
        status="draft",
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


class TestCareerPlanList:
    def test_list_plans_200(self, auth_headers, client, db_session):
        """列表查询返回 200。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        _seed_plan(db_session, user.id)
        resp = client.get("/api/career-plans", headers=auth_headers)
        assert resp.status_code == 200
        plans = resp.json()
        assert len(plans) >= 1
        assert "字节跳动" in plans[0]["goal_text"]


class TestCareerPlanDetail:
    def test_get_plan_200(self, auth_headers, client, db_session):
        """获取详情返回 200。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id)
        resp = client.get(f"/api/career-plans/{plan.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["goal_text"] == plan.goal_text
        assert resp.json()["timeline_months"] == 6

    def test_get_plan_404(self, auth_headers, client):
        """不存在的 ID 返回 404。"""
        resp = client.get(f"/api/career-plans/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


class TestMilestoneUpdate:
    def test_update_milestone_200(self, auth_headers, client, db_session):
        """更新里程碑状态返回 200。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id)
        resp = client.patch(
            f"/api/career-plans/{plan.id}/milestones/0",
            headers=auth_headers,
            json={"status": "in_progress"},
        )
        assert resp.status_code == 200
        milestones = resp.json()["milestones"]
        assert milestones[0]["status"] == "in_progress"
        # 其他里程碑不变
        assert milestones[1]["status"] == "pending"

    def test_update_milestone_404(self, auth_headers, client, db_session):
        """规划不存在时返回 404。"""
        resp = client.patch(
            f"/api/career-plans/{uuid.uuid4()}/milestones/0",
            headers=auth_headers,
            json={"status": "done"},
        )
        assert resp.status_code == 404
