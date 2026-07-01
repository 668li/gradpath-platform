# backend/tests/test_career_plans.py
"""职业规划 API 测试 — Phase 11 / Phase 12。"""
import uuid
from datetime import datetime, timedelta

from app.models.career_plan import CareerPlan
from app.models.user import User


def _seed_plan(db_session, user_id, milestones=None, status="draft"):
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
        status=status,
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


# ======================================================================
# Phase 12: 里程碑执行日志
# ======================================================================

class TestMilestoneLogCreate:
    def test_add_log_201(self, auth_headers, client, db_session):
        """添加执行日志返回 201。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id)
        resp = client.post(
            f"/api/career-plans/{plan.id}/milestones/0/logs",
            headers=auth_headers,
            json={"content": "今天学习了Go基础语法与并发模型"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"]
        assert data["plan_id"] == str(plan.id)
        assert data["milestone_index"] == 0
        assert "Go基础语法" in data["content"]
        assert data["created_at"] is not None

    def test_add_log_invalid_index_404(self, auth_headers, client, db_session):
        """里程碑索引越界返回 404。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id)
        resp = client.post(
            f"/api/career-plans/{plan.id}/milestones/99/logs",
            headers=auth_headers,
            json={"content": "无效索引"},
        )
        assert resp.status_code == 404

    def test_add_log_plan_not_found_404(self, auth_headers, client):
        """规划不存在时返回 404。"""
        resp = client.post(
            f"/api/career-plans/{uuid.uuid4()}/milestones/0/logs",
            headers=auth_headers,
            json={"content": "测试"},
        )
        assert resp.status_code == 404


class TestMilestoneLogList:
    def test_list_logs_200(self, auth_headers, client, db_session):
        """列出执行日志返回 200，且按创建时间倒序。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id)
        # 添加两条日志
        client.post(
            f"/api/career-plans/{plan.id}/milestones/0/logs",
            headers=auth_headers,
            json={"content": "第一条日志"},
        )
        client.post(
            f"/api/career-plans/{plan.id}/milestones/0/logs",
            headers=auth_headers,
            json={"content": "第二条日志"},
        )
        resp = client.get(
            f"/api/career-plans/{plan.id}/milestones/0/logs",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        logs = resp.json()
        assert len(logs) == 2
        # 倒序：最新（第二条）在前
        assert logs[0]["content"] == "第二条日志"
        assert logs[1]["content"] == "第一条日志"
        assert all(log["milestone_index"] == 0 for log in logs)

    def test_list_logs_empty(self, auth_headers, client, db_session):
        """无日志时返回空列表。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id)
        resp = client.get(
            f"/api/career-plans/{plan.id}/milestones/0/logs",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


class TestMilestoneLogDelete:
    def test_delete_log_204(self, auth_headers, client, db_session):
        """删除执行日志返回 204。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id)
        create = client.post(
            f"/api/career-plans/{plan.id}/milestones/0/logs",
            headers=auth_headers,
            json={"content": "待删除日志"},
        )
        log_id = create.json()["id"]
        resp = client.delete(
            f"/api/career-plans/{plan.id}/logs/{log_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 204
        # 再次查询应不包含该日志
        logs = client.get(
            f"/api/career-plans/{plan.id}/milestones/0/logs",
            headers=auth_headers,
        ).json()
        assert all(log["id"] != log_id for log in logs)

    def test_delete_log_not_found_404(self, auth_headers, client, db_session):
        """删除不存在的日志返回 404。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id)
        resp = client.delete(
            f"/api/career-plans/{plan.id}/logs/{uuid.uuid4()}",
            headers=auth_headers,
        )
        assert resp.status_code == 404


# ======================================================================
# Phase 12: 到期提醒
# ======================================================================

class TestReminders:
    def test_reminders_overdue_and_upcoming(self, auth_headers, client, db_session):
        """到期提醒正确分类 overdue 与 upcoming。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        today = datetime.utcnow().date()
        overdue_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        upcoming_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        far_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        done_date = (today - timedelta(days=5)).strftime("%Y-%m-%d")

        milestones = [
            {"title": "逾期任务", "description": "已过期", "target_date": overdue_date, "status": "pending"},
            {"title": "即将到期", "description": "3天后", "target_date": upcoming_date, "status": "pending"},
            {"title": "远期任务", "description": "30天后", "target_date": far_date, "status": "pending"},
            {"title": "已完成任务", "description": "已完成不提醒", "target_date": done_date, "status": "done"},
        ]
        plan = _seed_plan(db_session, user.id, milestones=milestones, status="active")

        resp = client.get("/api/career-plans/reminders", headers=auth_headers)
        assert resp.status_code == 200
        reminders = resp.json()
        # 仅 overdue + upcoming 共 2 条（远期与已完成不提醒）
        assert len(reminders) == 2

        types = sorted(r["type"] for r in reminders)
        assert types == ["overdue", "upcoming"]

        overdue = next(r for r in reminders if r["type"] == "overdue")
        assert overdue["milestone_title"] == "逾期任务"
        assert overdue["milestone_index"] == 0
        assert overdue["target_date"] == overdue_date
        assert overdue["days_remaining"] == -3
        assert overdue["plan_id"] == str(plan.id)
        assert "字节跳动" in overdue["plan_goal"]

        upcoming = next(r for r in reminders if r["type"] == "upcoming")
        assert upcoming["milestone_title"] == "即将到期"
        assert upcoming["milestone_index"] == 1
        assert upcoming["target_date"] == upcoming_date
        assert upcoming["days_remaining"] == 3

    def test_reminders_excludes_non_active_plans(self, auth_headers, client, db_session):
        """status != active 的规划不产生提醒。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        today = datetime.utcnow().date()
        overdue_date = (today - timedelta(days=3)).strftime("%Y-%m-%d")
        milestones = [
            {"title": "逾期任务", "description": "已过期", "target_date": overdue_date, "status": "pending"},
        ]
        # status=draft，不应产生提醒
        _seed_plan(db_session, user.id, milestones=milestones, status="draft")

        resp = client.get("/api/career-plans/reminders", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_reminders_empty(self, auth_headers, client, db_session):
        """无 active 规划时返回空列表。"""
        resp = client.get("/api/career-plans/reminders", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []


# ======================================================================
# Phase 12: 每日重点 (daily-focus)
# ======================================================================

class TestDailyFocus:
    def test_daily_focus_returns_pending_milestone(self, auth_headers, client, db_session):
        """active plan + pending milestone → 返回第一个 pending 里程碑。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        _seed_plan(db_session, user.id, status="active")

        resp = client.get("/api/career-plans/daily-focus", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["milestone_title"] == "掌握Go基础"
        assert item["milestone_index"] == 0
        assert item["status"] == "pending"
        assert item["has_logs"] is False
        assert "字节跳动" in item["plan_goal"]
        assert item["milestone_description"] == "学习Go语法"

    def test_daily_focus_prefers_in_progress(self, auth_headers, client, db_session):
        """in_progress 里程碑优先于 pending。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        milestones = [
            {"title": "任务A", "description": "待办", "status": "pending"},
            {"title": "任务B", "description": "进行中", "status": "in_progress"},
        ]
        _seed_plan(db_session, user.id, milestones=milestones, status="active")

        resp = client.get("/api/career-plans/daily-focus", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["milestone_title"] == "任务B"
        assert data[0]["status"] == "in_progress"
        assert data[0]["milestone_index"] == 1

    def test_daily_focus_has_logs_true(self, auth_headers, client, db_session):
        """里程碑已有执行日志时 has_logs 为 True。"""
        from app.models.milestone_log import MilestoneLog

        user = db_session.query(User).filter(User.email == "test@example.com").first()
        plan = _seed_plan(db_session, user.id, status="active")
        db_session.add(
            MilestoneLog(plan_id=str(plan.id), milestone_index=0, content="日志")
        )
        db_session.commit()

        resp = client.get("/api/career-plans/daily-focus", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()[0]["has_logs"] is True

    def test_daily_focus_empty_when_no_active_plan(self, auth_headers, client, db_session):
        """无 active 规划时返回空列表。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        # draft 状态不参与每日重点
        _seed_plan(db_session, user.id, status="draft")

        resp = client.get("/api/career-plans/daily-focus", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_daily_focus_max_three(self, auth_headers, client, db_session):
        """最多返回 3 条（创建 4 个 active 规划）。"""
        user = db_session.query(User).filter(User.email == "test@example.com").first()
        for _ in range(4):
            _seed_plan(db_session, user.id, status="active")

        resp = client.get("/api/career-plans/daily-focus", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 3
