# tests/test_p1_skill_channels.py
"""P1 skill 通道测试 — 学习计划师落库 micro-actions + 公告解读器。

覆盖：create_plan_from_tasks（守卫/校验）、learning_plan 微行动计划校验、
chat 全链路落库（mock LLM）、公告解读器 inject_data 诚实降级、announcements 搜索器。
"""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, patch

# 确保 backend/app 在 path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import pytest

from app.services.data_search_service import (
    detect_data_intents,
    search_announcements,
)


# ======================================================================
# create_plan_from_tasks
# ======================================================================


@pytest.fixture
def svc_user(db_session):
    from app.models.user import User

    user = User(email="p1@example.com", password_hash="x", name="P1测试")
    db_session.add(user)
    db_session.commit()
    return user


_VALID_TASKS = [
    {
        "day_number": i,
        "task_type": "practice",
        "title": f"行动{i}",
        "description": "具体做法说明",
        "estimated_minutes": 30,
    }
    for i in range(1, 5)
]


class TestCreatePlanFromTasks:
    def test_creates_plan_and_tasks(self, db_session, svc_user):
        from app.models.micro_action import MicroActionPlan, MicroActionTask
        from app.services.micro_action_service import create_plan_from_tasks

        plan = create_plan_from_tasks(
            db_session, svc_user.id, "kaoyan", "考研基础轮", _VALID_TASKS
        )
        assert plan.status == "active"
        assert plan.target_path == "kaoyan"
        tasks = (
            db_session.query(MicroActionTask)
            .filter(MicroActionTask.plan_id == plan.id)
            .all()
        )
        assert len(tasks) == 4
        assert {t.day_number for t in tasks} == {1, 2, 3, 4}

    def test_empty_tasks_raises(self, db_session, svc_user):
        from app.services.micro_action_service import create_plan_from_tasks

        with pytest.raises(ValueError):
            create_plan_from_tasks(db_session, svc_user.id, "kaoyan", None, [])

    def test_abandons_previous_active_plan(self, db_session, svc_user):
        from app.services.micro_action_service import (
            create_plan,
            create_plan_from_tasks,
        )

        old = create_plan(db_session, svc_user.id, "employment")
        new = create_plan_from_tasks(
            db_session, svc_user.id, "kaoyan", None, _VALID_TASKS
        )
        db_session.refresh(old)
        assert old.status == "abandoned"
        assert new.status == "active"


# ======================================================================
# learning_plan_generator 微行动计划校验
# ======================================================================


class TestValidateMicroActionPlan:
    def _skill(self):
        from app.skills.learning_plan_generator import LearningPlanGeneratorSkill

        return LearningPlanGeneratorSkill()

    def test_valid_plan_normalizes(self):
        import json

        from app.skills.learning_plan_generator import LearningPlanGeneratorSkill

        data = {
            "content": "计划",
            "micro_action_plan": {
                "target_path": "考公",  # 非法值 → 兜底 employment
                "target_role": "x" * 300,
                "tasks": [
                    {"day_number": 1, "task_type": "研究", "title": "a", "description": "b"},
                    {"day_number": 99, "task_type": "practice", "title": "c", "description": "d", "estimated_minutes": 999},
                    {"day_number": 3, "task_type": "reflect", "title": "e", "description": "f"},
                    {"day_number": 3, "task_type": "reflect", "title": "重复日", "description": "g"},
                    {"day_number": 4, "title": "缺描述"},
                ],
            },
        }
        result = LearningPlanGeneratorSkill().parse_response(
            json.dumps(data, ensure_ascii=False)
        )
        plan = result["micro_action_plan"]
        assert plan is not None
        assert plan["target_path"] == "employment"
        assert len(plan["target_role"]) <= 100
        # day 99 被 clamp 到 7；day 3 重复只保留首个；缺描述被剔除
        assert [t["day_number"] for t in plan["tasks"]] == [1, 7, 3]
        assert plan["tasks"][0]["task_type"] == "practice"  # 非法 task_type 兜底
        assert plan["tasks"][1]["estimated_minutes"] == 180  # clamp 上限

    def test_too_few_valid_tasks_returns_none(self):
        from app.skills.learning_plan_generator import _validate_micro_action_plan

        data = {
            "micro_action_plan": {
                "target_path": "kaoyan",
                "tasks": [{"day_number": 1, "task_type": "practice", "title": "a", "description": "b"}],
            }
        }
        assert _validate_micro_action_plan(data) is None

    def test_missing_plan_returns_none(self):
        from app.skills.learning_plan_generator import _validate_micro_action_plan

        assert _validate_micro_action_plan({"content": "纯文本"}) is None


# ======================================================================
# chat 全链路：学习计划师落库（mock LLM，仿 test_chat.py 模式）
# ======================================================================

MOCK_LEARNING_PLAN_REPLY = """{
  "content": "这是你的考研学习计划总览……（Markdown 正文）",
  "total_weeks": 12,
  "phases": [{"name": "基础", "weeks": "1-4", "goals": ["g"], "tasks": ["t"], "daily_hours": 3}],
  "milestones": ["m"],
  "resources": ["r"],
  "micro_action_plan": {
    "target_path": "kaoyan",
    "target_role": "三个月完成基础轮",
    "tasks": [
      {"day_number": 1, "task_type": "research", "title": "查目标院校近三年复试线", "description": "在研招网查 3 所院校并记录", "estimated_minutes": 40},
      {"day_number": 2, "task_type": "practice", "title": "数学基础 30 题", "description": "高数第一章 30 题，正确率≥70%", "estimated_minutes": 60},
      {"day_number": 3, "task_type": "reflect", "title": "复盘本周错题", "description": "整理错题本并归类错误原因", "estimated_minutes": 30}
    ]
  }
}"""


@pytest.fixture
def chat_client(client, auth_headers):
    """建好对话并返回 (client, headers, conversation_id)。"""
    resp = client.post(
        "/api/chat/conversations", json={"title": "计划冒烟"}, headers=auth_headers
    )
    assert resp.status_code in (200, 201), resp.text
    return client, auth_headers, resp.json()["id"]


class TestChatMicroPlanChannel:
    def _send(self, client, headers, conv_id, content="帮我制定考研学习计划"):
        return client.post(
            f"/api/chat/conversations/{conv_id}/messages",
            json={"content": content, "skill_hint": "learning_plan_generator"},
            headers=headers,
        )

    def test_micro_plan_saved_via_chat(self, chat_client, db_session, monkeypatch):
        from app.models.micro_action import MicroActionPlan, MicroActionTask
        from app.services import ai_service

        client, headers, conv_id = chat_client
        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")
        with patch.object(
            ai_service.AIService, "chat", AsyncMock(return_value=MOCK_LEARNING_PLAN_REPLY)
        ):
            resp = self._send(client, headers, conv_id)

        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["skill_used"] == "learning_plan_generator"
        assert data["micro_action_plan"]

        plan = (
            db_session.query(MicroActionPlan)
            .filter(MicroActionPlan.id == data["micro_action_plan"])
            .first()
        )
        assert plan is not None and plan.target_path == "kaoyan"
        tasks = (
            db_session.query(MicroActionTask)
            .filter(MicroActionTask.plan_id == plan.id)
            .order_by(MicroActionTask.day_number)
            .all()
        )
        assert [t.day_number for t in tasks] == [1, 2, 3]
        assert tasks[0].status == "pending"

    def test_invalid_llm_plan_degrades_to_reply_only(self, chat_client, monkeypatch):
        from app.services import ai_service

        client, headers, conv_id = chat_client
        bad_reply = '{"content": "计划建议（计划本体缺失）", "total_weeks": 8}'
        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")
        with patch.object(ai_service.AIService, "chat", AsyncMock(return_value=bad_reply)):
            resp = self._send(client, headers, conv_id)

        assert resp.status_code == 200
        data = resp.json()
        assert data["content"].startswith("计划建议")
        assert data["micro_action_plan"] is None


# ======================================================================
# 公告解读器
# ======================================================================


@pytest.fixture
def seed_announcement(db_session):
    from datetime import datetime

    from app.models.kaoyan_news import KaoyanNews

    row = KaoyanNews(
        title="测试大学 2027 年硕士研究生招生简章",
        summary="我校 2027 年拟招收硕士研究生 5000 名，计算机专业统考科目调整为 408。",
        content="全文……" * 10,
        source_platform="official",
        source_url="https://gs.test.edu.cn/zhaosheng",
        status="approved",
        category="官方公告·测试大学研究生院",
        published_at=datetime(2026, 9, 1, 10, 0, 0),
    )
    db_session.add(row)
    db_session.commit()
    return row


class TestAnnouncementInterpreter:
    def test_registered_and_active(self):
        from app.skills.registry import find_skill_instance, get_skill

        info = get_skill("announcement_interpreter")
        assert info is not None and info["is_active"] is True
        inst = find_skill_instance("刚出的招生简章帮我解读一下", {})
        assert inst is not None and inst.code == "announcement_interpreter"

    def test_injects_announcement_with_source(self, db_session, seed_announcement):
        from app.skills.announcement_interpreter import AnnouncementInterpreterSkill

        skill = AnnouncementInterpreterSkill()
        assert skill.covered_data_domains == {"announcements"}
        out = skill.inject_data(db_session, "u1", "测试大学的简章有什么要注意的")
        assert "测试大学" in out
        assert "gs.test.edu.cn" in out
        assert "408" in out

    def test_empty_honest_degradation(self, db_session):
        from app.skills.announcement_interpreter import AnnouncementInterpreterSkill

        out = AnnouncementInterpreterSkill().inject_data(
            db_session, "u1", "unknown 大学的简章"
        )
        assert "暂无" in out and "禁止编造" in out

    def test_prompt_discipline(self):
        from app.skills.announcement_interpreter import AnnouncementInterpreterSkill

        prompt = AnnouncementInterpreterSkill().build_system_prompt("用户：测试大学", [])
        assert "不猜" in prompt or "禁止编造" in prompt
        assert "行动项" in prompt or "今天" in prompt


class TestAnnouncementSearcher:
    def test_intent_detected(self):
        intents = detect_data_intents("最新的招生简章出了吗")
        assert any(i.domain == "announcements" for i in intents)

    def test_search_hits_kaoyan_news(self, db_session, seed_announcement):
        hits = search_announcements(db_session, "测试大学")
        assert len(hits) == 1
        assert hits[0].url == "https://gs.test.edu.cn/zhaosheng"
        assert hits[0].year == 2026

    def test_search_no_keyword_returns_latest(self, db_session, seed_announcement):
        assert len(search_announcements(db_session, None)) == 1

    def test_search_empty_db_returns_empty(self, db_session):
        assert search_announcements(db_session, "不存在") == []
