# backend/tests/test_export.py
"""数据导出服务与 API 测试 — PDF 时间线、JSON 备份、技能分享。"""
from datetime import date

from app.models.career_event import CareerEvent, EventType
from app.models.community_report import CommunityReport, DestinationType as CommunityDestType
from app.models.destination_decision import DecisionStatus, DestinationDecision
from app.models.employment_data import Degree
from app.models.interview_report import InterviewReport
from app.models.retrospective import PeriodType, Retrospective
from app.models.skill_node import SkillNode
from app.models.user import User
from app.models.user_setting import UserSetting
from app.services.export_service import (
    export_profile_json,
    export_timeline_pdf,
    get_shareable_skills,
)


# ======================================================================
# 辅助：构造一份包含全部数据类型的用户档案
# ======================================================================

def _seed_full_profile(db_session, user_id):
    """为某用户创建包含各表的完整测试数据。"""
    # 1 个去向决策
    db_session.add(DestinationDecision(
        user_id=user_id,
        destination_type="employment",
        status=DecisionStatus.confirmed,
        decision_date=date(2025, 5, 1),
        confidence=4,
        reasoning="大厂平台好",
        details={"company": "腾讯", "position": "后端"},
    ))
    # 2 个职业事件
    db_session.add(CareerEvent(
        user_id=user_id,
        event_date=date(2024, 7, 1),
        event_type=EventType.onboard,
        title="入职腾讯",
        description="后端开发工程师",
    ))
    db_session.add(CareerEvent(
        user_id=user_id,
        event_date=date(2025, 4, 1),
        event_type=EventType.promotion,
        title="晋升 T8",
    ))
    # 2 个技能节点
    db_session.add(SkillNode(
        user_id=user_id,
        name="Python",
        category="后端",
        level=4,
        acquired_date=date(2024, 1, 1),
        notes="主力语言",
    ))
    db_session.add(SkillNode(
        user_id=user_id,
        name="FastAPI",
        category="后端",
        level=3,
        acquired_date=date(2024, 8, 1),
    ))
    # 1 个复盘
    db_session.add(Retrospective(
        user_id=user_id,
        period_type=PeriodType.annual,
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        title="2024 年度复盘",
        achievements=["完成首个项目"],
        challenges="时间管理",
        lessons_learned="优先级很重要",
        next_steps=["学习系统设计"],
        satisfaction=4,
    ))
    # 1 个社区报告
    db_session.add(CommunityReport(
        user_id=user_id,
        school_name="测试大学",
        major="计算机",
        graduation_year=2024,
        degree=Degree.bachelor,
        destination_type=CommunityDestType.employment,
        employer="腾讯",
        city="深圳",
    ))
    # 1 个面试报告
    db_session.add(InterviewReport(
        user_id=user_id,
        company="腾讯",
        position="后端",
        interview_year=2024,
        rounds=3,
        result="offer",
        difficulty=4,
        summary="偏算法与系统设计",
    ))
    db_session.commit()


# ======================================================================
# PDF 导出
# ======================================================================

class TestPdfExport:
    def test_pdf_requires_auth(self, client):
        resp = client.get("/api/export/timeline.pdf")
        assert resp.status_code == 401

    def test_pdf_success(self, client, auth_headers, db_session):
        user = db_session.query(User).first()
        _seed_full_profile(db_session, user.id)

        resp = client.get("/api/export/timeline.pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        # PDF magic header
        assert resp.content[:4] == b"%PDF"
        assert len(resp.content) > 100
        # Content-Disposition 附件下载
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert "gradpath-timeline.pdf" in resp.headers.get("content-disposition", "")

    def test_pdf_empty_user(self, client, auth_headers):
        """无任何数据的用户仍应能导出 PDF。"""
        resp = client.get("/api/export/timeline.pdf", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content[:4] == b"%PDF"

    def test_pdf_service_directly(self, db_session, auth_headers):
        """直接调用服务函数验证返回 bytes。"""
        user = db_session.query(User).first()
        pdf_bytes = export_timeline_pdf(db_session, user.id)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes[:4] == b"%PDF"
        assert b"/Type /Catalog" in pdf_bytes or b"endobj" in pdf_bytes


# ======================================================================
# JSON 备份
# ======================================================================

class TestJsonExport:
    def test_json_requires_auth(self, client):
        resp = client.get("/api/export/profile.json")
        assert resp.status_code == 401

    def test_json_success_all_sections(self, client, auth_headers, db_session):
        user = db_session.query(User).first()
        _seed_full_profile(db_session, user.id)

        resp = client.get("/api/export/profile.json", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()

        # 校验所有顶层 section 都存在
        for section in [
            "profile",
            "gamification",
            "decisions",
            "events",
            "skills",
            "retrospectives",
            "community_reports",
            "interview_reports",
        ]:
            assert section in data, f"缺少 section: {section}"

        # profile
        assert data["profile"]["name"] == "测试用户"
        assert data["profile"]["email"] == "test@example.com"

        # gamification
        assert data["gamification"]["xp"] > 0
        assert data["gamification"]["level"] >= 1
        assert isinstance(data["gamification"]["level_name"], str)

        # decisions
        assert len(data["decisions"]) == 1
        assert data["decisions"][0]["destination_type"] == "employment"
        assert data["decisions"][0]["confidence"] == 4
        assert data["decisions"][0]["decision_date"] == "2025-05-01"
        assert isinstance(data["decisions"][0]["id"], str)

        # events
        assert len(data["events"]) == 2
        assert data["events"][0]["event_date"] == "2024-07-01"
        assert data["events"][1]["event_date"] == "2025-04-01"

        # skills
        assert len(data["skills"]) == 2
        skill_names = {s["name"] for s in data["skills"]}
        assert skill_names == {"Python", "FastAPI"}
        assert all(isinstance(s["id"], str) for s in data["skills"])

        # retrospectives
        assert len(data["retrospectives"]) == 1
        assert data["retrospectives"][0]["title"] == "2024 年度复盘"
        assert data["retrospectives"][0]["period_start"] == "2024-01-01"

        # community_reports
        assert len(data["community_reports"]) == 1
        assert data["community_reports"][0]["school_name"] == "测试大学"
        assert data["community_reports"][0]["degree"] == "bachelor"

        # interview_reports
        assert len(data["interview_reports"]) == 1
        assert data["interview_reports"][0]["company"] == "腾讯"
        assert data["interview_reports"][0]["interview_year"] == 2024

    def test_json_empty_user(self, client, auth_headers):
        """无数据用户的 JSON 各列表为空但结构完整。"""
        resp = client.get("/api/export/profile.json", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile"]["name"] == "测试用户"
        assert data["gamification"]["xp"] == 0
        assert data["decisions"] == []
        assert data["events"] == []
        assert data["skills"] == []
        assert data["retrospectives"] == []
        assert data["community_reports"] == []
        assert data["interview_reports"] == []

    def test_json_service_directly(self, db_session, auth_headers):
        """直接调用服务函数验证返回 dict。"""
        user = db_session.query(User).first()
        result = export_profile_json(db_session, user.id)
        assert isinstance(result, dict)
        assert "profile" in result and "gamification" in result


# ======================================================================
# 公开技能分享
# ======================================================================

class TestShareSkills:
    def test_invalid_token_returns_404(self, client):
        """数据库中不存在的 token 返回 404。"""
        resp = client.get("/api/share/skills/nonexistent-token")
        assert resp.status_code == 404
        assert "无效" in resp.json()["detail"] or "已关闭" in resp.json()["detail"]

    def test_empty_token_returns_404(self, client):
        """空 token 返回 404。"""
        resp = client.get("/api/share/skills/")
        assert resp.status_code == 404

    def test_share_disabled_returns_404(self, client, db_session, auth_headers):
        """token 存在但分享已关闭 → 404。"""
        user = db_session.query(User).first()
        setting = UserSetting(
            user_id=user.id,
            share_skills_enabled=False,
            share_token="disabled-token-123",
        )
        db_session.add(setting)
        db_session.commit()

        resp = client.get("/api/share/skills/disabled-token-123")
        assert resp.status_code == 404

    def test_share_enabled_returns_skills(self, client, db_session, auth_headers):
        """开启分享且存在技能 → 200，返回 user_name 与 skills。"""
        user = db_session.query(User).first()
        # 创建分享设置
        setting = UserSetting(
            user_id=user.id,
            share_skills_enabled=True,
            share_token="valid-share-token-456",
        )
        db_session.add(setting)
        # 创建技能节点
        db_session.add(SkillNode(
            user_id=user.id,
            name="Python",
            category="后端",
            level=4,
            acquired_date=date(2024, 1, 1),
            notes="主力语言",
        ))
        db_session.add(SkillNode(
            user_id=user.id,
            name="React",
            category="前端",
            level=3,
        ))
        db_session.commit()

        resp = client.get("/api/share/skills/valid-share-token-456")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_name"] == "测试用户"
        assert isinstance(data["skills"], list)
        assert len(data["skills"]) == 2

        # 校验技能字段结构
        skill = data["skills"][0]
        for field in ["id", "name", "category", "level",
                      "parent_id", "acquired_date", "notes"]:
            assert field in skill, f"缺少字段: {field}"

        # 不应包含任何个人数据（无 email、无 decisions 等）
        assert "email" not in data
        assert "decisions" not in data
        assert "profile" not in data

    def test_share_enabled_no_skills(self, client, db_session, auth_headers):
        """开启分享但用户没有技能 → 200，skills 为空列表。"""
        user = db_session.query(User).first()
        db_session.add(UserSetting(
            user_id=user.id,
            share_skills_enabled=True,
            share_token="empty-skills-token-789",
        ))
        db_session.commit()

        resp = client.get("/api/share/skills/empty-skills-token-789")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_name"] == "测试用户"
        assert data["skills"] == []

    def test_share_service_directly(self, db_session, auth_headers):
        """直接调用服务函数验证返回 dict / None。"""
        user = db_session.query(User).first()
        # 无效 token → None
        assert get_shareable_skills(db_session, "no-such-token") is None

        # 有效 token → dict
        db_session.add(UserSetting(
            user_id=user.id,
            share_skills_enabled=True,
            share_token="direct-call-token",
        ))
        db_session.add(SkillNode(
            user_id=user.id,
            name="Go",
            category="后端",
            level=2,
        ))
        db_session.commit()
        result = get_shareable_skills(db_session, "direct-call-token")
        assert result is not None
        assert result["user_name"] == "测试用户"
        assert len(result["skills"]) == 1
        assert result["skills"][0]["name"] == "Go"
