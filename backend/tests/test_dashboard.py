from datetime import datetime, timedelta

from app.models.career_plan import CareerPlan
from app.models.milestone_log import MilestoneLog
from app.models.user import User


def test_dashboard_empty(auth_headers, client):
    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decisions_count"] == 0
    assert data["events_count"] == 0
    assert data["skills_count"] == 0
    assert data["retrospectives_count"] == 0
    assert data["latest_decision"] is None
    assert data["recent_events"] == []
    assert data["timeline"] == []


def test_dashboard_with_data(auth_headers, client):
    # 创建决策
    client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-01",
            "destination_type": "employment",
            "status": "confirmed",
            "details": {"company": "腾讯"},
            "reasoning": "...",
            "confidence": 4,
        },
    )
    # 创建事件
    for title in ["入职", "完成项目", "晋升"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": "2026-06-15",
                "event_type": "onboard",
                "title": title,
                "description": "...",
            },
        )
    # 创建技能
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "Python", "category": "后端", "level": 4},
    )

    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decisions_count"] == 1
    assert data["events_count"] == 3
    assert data["skills_count"] == 1
    assert data["latest_decision"] is not None
    assert len(data["recent_events"]) == 3
    # timeline 合并了决策和事件
    assert len(data["timeline"]) == 4


def test_dashboard_skill_categories(auth_headers, client):
    for cat in ["后端", "后端", "前端"]:
        client.post(
            "/api/skills",
            headers=auth_headers,
            json={"name": f"技能-{cat}", "category": cat, "level": 3},
        )
    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    data = resp.json()
    assert data["skill_categories"]["后端"] == 2
    assert data["skill_categories"]["前端"] == 1


# ======================================================================
# Phase 12: 周回顾 (weekly-recap)
# ======================================================================

def test_weekly_recap_structure_empty(auth_headers, client):
    """无数据时 weekly-recap 返回正确结构。"""
    resp = client.get("/api/dashboard/weekly-recap", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for key in [
        "completed_this_week",
        "logs_this_week",
        "upcoming_deadlines",
        "active_plans",
        "total_milestones_done",
        "total_milestones",
        "encouragement",
    ]:
        assert key in data
    assert data["completed_this_week"] == 0
    assert data["logs_this_week"] == 0
    assert data["upcoming_deadlines"] == []
    assert data["active_plans"] == 0
    assert data["total_milestones"] == 0
    assert data["total_milestones_done"] == 0
    assert isinstance(data["encouragement"], str)
    assert "还没有进展" in data["encouragement"]


def _seed_active_plan(db_session, user_id, milestones):
    plan = CareerPlan(
        user_id=user_id,
        goal_text="周回顾测试目标",
        current_state={},
        target_state={},
        gaps=[],
        milestones=milestones,
        timeline_months=3,
        status="active",
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)
    return plan


def test_weekly_recap_with_milestones(auth_headers, client, db_session):
    """有数据时 weekly-recap 统计 active 计划、里程碑总数与即将到期。"""
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    today = datetime.utcnow().date()
    soon = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    far = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    milestones = [
        {"title": "即将到期任务", "description": "3天后", "target_date": soon, "status": "pending"},
        {"title": "已完成任务", "description": "done", "status": "done"},
        {"title": "远期任务", "description": "30天后", "target_date": far, "status": "pending"},
    ]
    _seed_active_plan(db_session, user.id, milestones)

    resp = client.get("/api/dashboard/weekly-recap", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["active_plans"] == 1
    assert data["total_milestones"] == 3
    assert data["total_milestones_done"] == 1
    assert len(data["upcoming_deadlines"]) == 1
    assert data["upcoming_deadlines"][0]["milestone_title"] == "即将到期任务"
    assert data["upcoming_deadlines"][0]["days_remaining"] == 3
    # 无本周日志 → completed_this_week 为 0
    assert data["completed_this_week"] == 0
    assert data["logs_this_week"] == 0
    assert "还没有进展" in data["encouragement"]


def test_weekly_recap_encouragement_with_logs(auth_headers, client, db_session):
    """本周有日志的已完成里程碑计入 completed_this_week，鼓励语切换。"""
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    milestones = [
        {"title": "已完成任务", "description": "done", "status": "done"},
    ]
    plan = _seed_active_plan(db_session, user.id, milestones)
    db_session.add(
        MilestoneLog(plan_id=str(plan.id), milestone_index=0, content="完成记录")
    )
    db_session.commit()

    resp = client.get("/api/dashboard/weekly-recap", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["completed_this_week"] == 1
    assert data["logs_this_week"] == 1
    assert "保持势头" in data["encouragement"]
