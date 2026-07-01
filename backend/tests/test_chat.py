# backend/tests/test_chat.py
"""对话 API 测试 — Phase 11 AI 职业管家。"""
import json
from unittest.mock import patch

import httpx
import pytest

from app.models.career_plan import CareerPlan
from app.models.conversation import Conversation, Message


# ======================================================================
# 辅助函数与 mock 数据
# ======================================================================

MOCK_REPLY_PLAIN = "你好！我是 GradPath 职业管家，很高兴为你服务。"

MOCK_REPLY_CAREER_PLAN = json.dumps(
    {
        "content": "根据你的情况，我为你制定了 6 个月的进大厂规划。",
        "career_plan": {
            "goal": "6个月内进入字节跳动后端开发岗",
            "current_state": {"skills": "Python基础", "education": "本科", "experience": "无实习"},
            "target_state": {
                "position": "后端开发",
                "company": "字节跳动",
                "requirements": "Go/Java, 算法, 系统设计",
            },
            "gaps": [
                {"skill": "Go语言", "current_level": 1, "target_level": 4, "gap": "需系统学习"},
                {"skill": "系统设计", "current_level": 1, "target_level": 3, "gap": "缺乏经验"},
            ],
            "milestones": [
                {"title": "掌握Go基础", "description": "学习Go语法与并发", "deadline": "2025-03-01", "skills": ["Go"], "status": "pending"},
                {"title": "刷算法题200道", "description": "LeetCode中等难度", "deadline": "2025-05-01", "skills": ["算法"], "status": "pending"},
            ],
            "timeline_months": 6,
        },
    },
    ensure_ascii=False,
)


def _create_conversation(client, auth_headers, title="测试对话"):
    resp = client.post(
        "/api/chat/conversations", headers=auth_headers, json={"title": title}
    )
    assert resp.status_code == 201
    return resp.json()


# ======================================================================
# 对话 CRUD
# ======================================================================

class TestConversationCRUD:
    def test_create_conversation_200(self, auth_headers, client):
        """创建对话返回 201。"""
        resp = client.post(
            "/api/chat/conversations",
            headers=auth_headers,
            json={"title": "我的职业规划"},
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "我的职业规划"
        assert resp.json()["id"] is not None

    def test_create_conversation_401(self, client):
        """未登录创建对话返回 401。"""
        resp = client.post("/api/chat/conversations", json={"title": "test"})
        assert resp.status_code == 401

    def test_list_conversations_200(self, auth_headers, client):
        """列表查询返回 200。"""
        _create_conversation(client, auth_headers, "对话1")
        _create_conversation(client, auth_headers, "对话2")
        resp = client.get("/api/chat/conversations", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2
        assert len(data["items"]) >= 2

    def test_list_conversations_pagination(self, auth_headers, client):
        """分页参数生效。"""
        for i in range(5):
            _create_conversation(client, auth_headers, f"对话{i}")
        resp = client.get(
            "/api/chat/conversations?page=1&page_size=2", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) == 2
        assert data["total"] >= 5

    def test_delete_conversation_204(self, auth_headers, client):
        """删除对话返回 204。"""
        conv = _create_conversation(client, auth_headers)
        resp = client.delete(
            f"/api/chat/conversations/{conv['id']}", headers=auth_headers
        )
        assert resp.status_code == 204

    def test_delete_conversation_404(self, auth_headers, client):
        """删除不存在的对话返回 404。"""
        import uuid

        resp = client.delete(
            f"/api/chat/conversations/{uuid.uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404


# ======================================================================
# 发送消息
# ======================================================================

class TestSendMessage:
    def test_send_message_401(self, client):
        """未登录发送消息返回 401。"""
        import uuid

        resp = client.post(
            f"/api/chat/conversations/{uuid.uuid4()}/messages",
            json={"content": "你好"},
        )
        assert resp.status_code == 401

    def test_send_message_503_no_llm_key(self, auth_headers, client, db_session, monkeypatch):
        """LLM_API_KEY 未配置时返回 503。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "")
        conv = _create_conversation(client, auth_headers)
        resp = client.post(
            f"/api/chat/conversations/{conv['id']}/messages",
            headers=auth_headers,
            json={"content": "你好"},
        )
        assert resp.status_code == 503
        assert "未配置" in resp.json()["detail"]

    def test_send_message_success_with_mock(
        self, auth_headers, client, db_session, monkeypatch
    ):
        """mock LLM 返回纯文本，发送消息成功。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")
        conv = _create_conversation(client, auth_headers)

        with patch.object(
            ai_service.AIService,
            "chat",
            lambda self, sp, uc, timeout=30: MOCK_REPLY_PLAIN,
        ):
            resp = client.post(
                f"/api/chat/conversations/{conv['id']}/messages",
                headers=auth_headers,
                json={"content": "你好，请介绍一下你自己"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == MOCK_REPLY_PLAIN
        assert data["skill_used"] == "default"
        assert data["career_plan"] is None

    def test_send_message_with_skill_hint(
        self, auth_headers, client, db_session, monkeypatch
    ):
        """skill_hint 指定时使用对应 Skill。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")
        conv = _create_conversation(client, auth_headers)

        mock_interview_reply = json.dumps(
            {
                "content": "以下是为你准备的面试题。",
                "questions": ["请介绍一个你参与的项目", "解释 HTTPS 的原理"],
            },
            ensure_ascii=False,
        )

        captured = {}

        def fake_chat(self, system_prompt, user_content, timeout=30):
            captured["system"] = system_prompt
            return mock_interview_reply

        with patch.object(ai_service.AIService, "chat", fake_chat):
            resp = client.post(
                f"/api/chat/conversations/{conv['id']}/messages",
                headers=auth_headers,
                json={
                    "content": "我想准备面试",
                    "skill_hint": "interview_simulation",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_used"] == "interview_simulation"
        # system prompt 应包含面试模拟相关内容
        assert "面试" in captured["system"]


# ======================================================================
# 消息历史
# ======================================================================

class TestMessageHistory:
    def test_message_history_order(self, auth_headers, client, db_session, monkeypatch):
        """消息历史按时间升序返回。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")
        conv = _create_conversation(client, auth_headers)

        with patch.object(
            ai_service.AIService,
            "chat",
            lambda self, sp, uc, timeout=30: "回复1",
        ):
            client.post(
                f"/api/chat/conversations/{conv['id']}/messages",
                headers=auth_headers,
                json={"content": "第一条消息"},
            )
        with patch.object(
            ai_service.AIService,
            "chat",
            lambda self, sp, uc, timeout=30: "回复2",
        ):
            client.post(
                f"/api/chat/conversations/{conv['id']}/messages",
                headers=auth_headers,
                json={"content": "第二条消息"},
            )

        resp = client.get(
            f"/api/chat/conversations/{conv['id']}/messages",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        msgs = resp.json()
        # 应有 4 条消息（2 user + 2 assistant），按时间升序
        assert len(msgs) == 4
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "第一条消息"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == "回复1"
        assert msgs[2]["role"] == "user"
        assert msgs[2]["content"] == "第二条消息"
        assert msgs[3]["role"] == "assistant"
        assert msgs[3]["content"] == "回复2"


# ======================================================================
# Skill 列表
# ======================================================================

class TestSkillsList:
    def test_list_skills_returns_all(self, auth_headers, client):
        """列出全部 Skill（含 Phase 12 新增）。"""
        resp = client.get("/api/chat/skills", headers=auth_headers)
        assert resp.status_code == 200
        skills = resp.json()
        assert len(skills) == 6
        codes = [s["code"] for s in skills]
        assert "career_planning" in codes
        assert "grad_school_planning" in codes
        assert "career_transition" in codes
        assert "resume_diagnosis" in codes
        assert "interview_simulation" in codes
        assert "default" in codes


# ======================================================================
# 职业规划提取
# ======================================================================

class TestCareerPlanExtraction:
    def test_career_plan_saved_from_llm(
        self, auth_headers, client, db_session, monkeypatch
    ):
        """mock LLM 返回含 career_plan 的 JSON，验证规划被保存。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")
        conv = _create_conversation(client, auth_headers)

        with patch.object(
            ai_service.AIService,
            "chat",
            lambda self, sp, uc, timeout=30: MOCK_REPLY_CAREER_PLAN,
        ):
            resp = client.post(
                f"/api/chat/conversations/{conv['id']}/messages",
                headers=auth_headers,
                json={"content": "帮我规划一下如何进大厂"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_used"] == "career_planning"
        assert data["career_plan"] is not None

        # 验证 CareerPlan 已保存到 DB
        plans = db_session.query(CareerPlan).all()
        assert len(plans) >= 1
        plan = plans[-1]
        assert "字节跳动" in plan.goal_text
        assert plan.timeline_months == 6
        assert len(plan.gaps) == 2
        assert len(plan.milestones) == 2
        assert plan.status == "draft"

    def test_career_plan_listed_in_api(
        self, auth_headers, client, db_session, monkeypatch
    ):
        """生成的职业规划可通过 career-plans API 查询。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")
        conv = _create_conversation(client, auth_headers)

        with patch.object(
            ai_service.AIService,
            "chat",
            lambda self, sp, uc, timeout=30: MOCK_REPLY_CAREER_PLAN,
        ):
            client.post(
                f"/api/chat/conversations/{conv['id']}/messages",
                headers=auth_headers,
                json={"content": "帮我做职业规划"},
            )

        resp = client.get("/api/career-plans", headers=auth_headers)
        assert resp.status_code == 200
        plans = resp.json()
        assert len(plans) >= 1
        assert "字节跳动" in plans[0]["goal_text"]
