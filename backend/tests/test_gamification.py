# backend/tests/test_gamification.py
"""游戏化服务与 API 测试。"""
from datetime import date

from app.models.career_event import CareerEvent, EventType
from app.models.community_report import CommunityReport, DestinationType
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.models.employment_data import Degree
from app.models.interview_report import InterviewReport
from app.models.retrospective import PeriodType, Retrospective
from app.models.skill_node import SkillNode
from app.models.user import User
from app.services.gamification_service import (
    LEVEL_THRESHOLDS,
    calculate_xp,
    check_and_award_badges,
    get_level,
    get_or_create_settings,
    get_profile,
    update_settings,
)


# ======================================================================
# XP 计算
# ======================================================================

class TestCalculateXP:
    def test_empty_user(self, db_session, auth_headers):
        user = db_session.query(User).first()
        xp = calculate_xp(db_session, user.id)
        assert xp == 0

    def test_decisions_only(self, db_session, auth_headers):
        user = db_session.query(User).first()
        for _ in range(3):
            db_session.add(DestinationDecision(
                user_id=user.id,
                destination_type="employment",
                status=DecisionStatus.planned,
                decision_date=date(2025, 1, 1),
                confidence=3,
            ))
        db_session.commit()
        xp = calculate_xp(db_session, user.id)
        assert xp == 30  # 3 * 10

    def test_all_types(self, db_session, auth_headers):
        user = db_session.query(User).first()
        # 1 decision = 10
        db_session.add(DestinationDecision(
            user_id=user.id,
            destination_type="employment",
            status=DecisionStatus.planned,
            decision_date=date(2025, 1, 1),
            confidence=3,
        ))
        # 2 events (1 promotion) = 5 + 15 = 20
        db_session.add(CareerEvent(
            user_id=user.id,
            event_date=date(2025, 1, 1),
            event_type=EventType.onboard,
            title="入职",
        ))
        db_session.add(CareerEvent(
            user_id=user.id,
            event_date=date(2025, 3, 1),
            event_type=EventType.promotion,
            title="晋升",
        ))
        # 1 skill level 3 = 15
        db_session.add(SkillNode(
            user_id=user.id,
            name="Python",
            category="编程",
            level=3,
        ))
        # 1 retro = 15
        db_session.add(Retrospective(
            user_id=user.id,
            period_type=PeriodType.annual,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 12, 31),
            title="年度复盘",
            satisfaction=4,
        ))
        # 1 community report = 20
        db_session.add(CommunityReport(
            user_id=user.id,
            school_name="测试大学",
            major="计算机",
            graduation_year=2025,
            degree=Degree.bachelor,
            destination_type=DestinationType.employment,
        ))
        # 1 interview report = 20
        db_session.add(InterviewReport(
            user_id=user.id,
            company="测试公司",
            position="后端",
            interview_year=2025,
            result="offer",
        ))
        db_session.commit()
        xp = calculate_xp(db_session, user.id)
        assert xp == 100  # 10 + 20 + 15 + 15 + 20 + 20


# ======================================================================
# 等级系统
# ======================================================================

class TestLevelSystem:
    def test_level_1_at_zero(self):
        level, name, cur, nxt = get_level(0)
        assert level == 1
        assert name == "萌新"
        assert cur == 0
        assert nxt == 50

    def test_level_2_at_50(self):
        level, name, _, _ = get_level(50)
        assert level == 2
        assert name == "探索者"

    def test_level_3_at_150(self):
        level, name, _, _ = get_level(150)
        assert level == 3
        assert name == "前行者"

    def test_level_5_at_700(self):
        level, name, _, _ = get_level(700)
        assert level == 5
        assert name == "达人"

    def test_level_7_at_2000(self):
        level, name, cur, nxt = get_level(2000)
        assert level == 7
        assert name == "大师"
        assert nxt == 2000  # max level, next == current


# ======================================================================
# 徽章颁发
# ======================================================================

class TestBadgeAwarding:
    def test_first_decision_badge(self, db_session, auth_headers):
        user = db_session.query(User).first()
        db_session.add(DestinationDecision(
            user_id=user.id,
            destination_type="employment",
            status=DecisionStatus.planned,
            decision_date=date(2025, 1, 1),
            confidence=3,
        ))
        db_session.commit()
        awarded, _ = check_and_award_badges(db_session, user.id)
        codes = [b["code"] for b in awarded]
        assert "first_decision" in codes

    def test_first_event_badge(self, db_session, auth_headers):
        user = db_session.query(User).first()
        db_session.add(CareerEvent(
            user_id=user.id,
            event_date=date(2025, 1, 1),
            event_type=EventType.onboard,
            title="入职",
        ))
        db_session.commit()
        awarded, _ = check_and_award_badges(db_session, user.id)
        codes = [b["code"] for b in awarded]
        assert "first_event" in codes

    def test_decision_master_badge(self, db_session, auth_headers):
        user = db_session.query(User).first()
        for _ in range(5):
            db_session.add(DestinationDecision(
                user_id=user.id,
                destination_type="employment",
                status=DecisionStatus.planned,
                decision_date=date(2025, 1, 1),
                confidence=3,
            ))
        db_session.commit()
        awarded, _ = check_and_award_badges(db_session, user.id)
        codes = [b["code"] for b in awarded]
        assert "decision_master" in codes

    def test_badge_idempotency(self, db_session, auth_headers):
        user = db_session.query(User).first()
        db_session.add(DestinationDecision(
            user_id=user.id,
            destination_type="employment",
            status=DecisionStatus.planned,
            decision_date=date(2025, 1, 1),
            confidence=3,
        ))
        db_session.commit()
        # First call awards the badge
        first, _ = check_and_award_badges(db_session, user.id)
        assert len(first) > 0
        # Second call should not re-award
        second, _ = check_and_award_badges(db_session, user.id)
        assert len(second) == 0


# ======================================================================
# Profile API
# ======================================================================

class TestGamificationAPI:
    def test_profile_requires_auth(self, client):
        resp = client.get("/api/gamification/profile")
        assert resp.status_code == 401

    def test_profile_returns_correct_xp(self, client, auth_headers, db_session):
        user = db_session.query(User).first()
        db_session.add(DestinationDecision(
            user_id=user.id,
            destination_type="employment",
            status=DecisionStatus.planned,
            decision_date=date(2025, 1, 1),
            confidence=3,
        ))
        db_session.commit()
        resp = client.get("/api/gamification/profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["xp"] == 10
        assert data["level"] == 1

    def test_profile_newly_awarded_on_first_access(self, client, auth_headers, db_session):
        user = db_session.query(User).first()
        db_session.add(CareerEvent(
            user_id=user.id,
            event_date=date(2025, 1, 1),
            event_type=EventType.onboard,
            title="入职",
        ))
        db_session.commit()
        resp = client.get("/api/gamification/profile", headers=auth_headers)
        data = resp.json()
        codes = [b["code"] for b in data["newly_awarded"]]
        assert "first_event" in codes

    def test_profile_second_access_no_new_badges(self, client, auth_headers, db_session):
        user = db_session.query(User).first()
        db_session.add(CareerEvent(
            user_id=user.id,
            event_date=date(2025, 1, 1),
            event_type=EventType.onboard,
            title="入职",
        ))
        db_session.commit()
        client.get("/api/gamification/profile", headers=auth_headers)
        resp = client.get("/api/gamification/profile", headers=auth_headers)
        data = resp.json()
        assert len(data["newly_awarded"]) == 0


# ======================================================================
# Settings API
# ======================================================================

class TestSettingsAPI:
    def test_settings_require_auth(self, client):
        resp = client.get("/api/gamification/settings")
        assert resp.status_code == 401

    def test_default_settings(self, client, auth_headers):
        resp = client.get("/api/gamification/settings", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["share_skills_enabled"] is False
        assert data["share_token"] is None

    def test_enable_share_generates_token(self, client, auth_headers):
        resp = client.patch(
            "/api/gamification/settings",
            headers=auth_headers,
            json={"share_skills_enabled": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["share_skills_enabled"] is True
        assert data["share_token"] is not None
        assert len(data["share_token"]) > 0

    def test_disable_share_keeps_token(self, client, auth_headers):
        # Enable first
        resp1 = client.patch(
            "/api/gamification/settings",
            headers=auth_headers,
            json={"share_skills_enabled": True},
        )
        token = resp1.json()["share_token"]
        # Disable
        resp2 = client.patch(
            "/api/gamification/settings",
            headers=auth_headers,
            json={"share_skills_enabled": False},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["share_skills_enabled"] is False
        assert data["share_token"] == token  # token preserved
