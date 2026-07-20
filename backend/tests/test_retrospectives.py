import json
from datetime import date
from unittest.mock import AsyncMock, patch

import httpx

from app.models.career_event import CareerEvent, EventType


def test_create_retrospective(auth_headers, client):
    resp = client.post(
        "/api/retrospectives",
        headers=auth_headers,
        json={
            "period_type": "annual",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "title": "2025年度复盘",
            "achievements": ["晋升P6", "主导核心项目"],
            "challenges": "跨团队协作困难",
            "lessons_learned": "沟通需要更前置",
            "next_steps": ["提升架构能力", "拓展技术视野"],
            "satisfaction": 4,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "2025年度复盘"
    assert len(data["achievements"]) == 2
    assert data["satisfaction"] == 4


def test_list_retrospectives(auth_headers, client):
    for i in range(3):
        client.post(
            "/api/retrospectives",
            headers=auth_headers,
            json={
                "period_type": "quarterly",
                "period_start": "2025-01-01",
                "period_end": "2025-03-31",
                "title": f"Q{i+1}复盘",
                "achievements": [],
                "challenges": "...",
                "lessons_learned": "...",
                "next_steps": [],
                "satisfaction": 3,
            },
        )
    resp = client.get("/api/retrospectives", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3


def test_retrospective_draft(auth_headers, client):
    # 创建几个事件
    for title in ["完成A项目", "获得PMP证书", "晋升"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": "2025-06-15",
                "event_type": "project_done",
                "title": title,
                "description": "...",
            },
        )
    resp = client.get(
        "/api/retrospectives/draft?period_start=2025-01-01&period_end=2025-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["event_summaries"]) == 3
    assert "完成A项目" in [e["title"] for e in data["event_summaries"]]


def test_update_retrospective(auth_headers, client):
    create = client.post(
        "/api/retrospectives",
        headers=auth_headers,
        json={
            "period_type": "custom",
            "period_start": "2025-01-01",
            "period_end": "2025-06-30",
            "title": "半年复盘",
            "achievements": [],
            "challenges": "",
            "lessons_learned": "",
            "next_steps": [],
            "satisfaction": 3,
        },
    )
    rid = create.json()["id"]
    resp = client.patch(
        f"/api/retrospectives/{rid}",
        headers=auth_headers,
        json={"satisfaction": 5, "achievements": ["新成就"]},
    )
    assert resp.status_code == 200
    assert resp.json()["satisfaction"] == 5
    assert resp.json()["achievements"] == ["新成就"]


# ======================================================================
# AI 复盘草稿
# ======================================================================

MOCK_RETRO_DRAFT_RESPONSE = json.dumps(
    {
        "achievements": ["完成核心系统重构", "通过PMP认证"],
        "challenges": "跨团队协作存在沟通瓶颈，需求变更频繁导致进度压力。",
        "lessons_learned": "前置沟通与需求确认能有效降低返工率，架构设计需提前考虑扩展性。",
        "next_steps": ["推动架构评审机制落地", "建立跨团队周会同步机制"],
        "suggested_satisfaction": 4,
        "summary": "本季度整体进展顺利，核心项目按时交付，但跨团队协作仍有改进空间。",
    },
    ensure_ascii=False,
)


def _ai_draft_payload(**overrides):
    """构造 AI 复盘草稿请求体。"""
    payload = {
        "period_start": "2025-01-01",
        "period_end": "2025-12-31",
    }
    payload.update(overrides)
    return payload


def test_ai_draft_requires_auth(client):
    """未登录不能调用 AI 复盘草稿。"""
    resp = client.post("/api/retrospectives/ai-draft", json=_ai_draft_payload())
    assert resp.status_code == 401


def test_ai_draft_no_llm_key_returns_503(auth_headers, client, db_session, monkeypatch):
    """LLM_API_KEY 未配置时返回 503。"""
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "")

    resp = client.post(
        "/api/retrospectives/ai-draft",
        headers=auth_headers,
        json=_ai_draft_payload(),
    )
    assert resp.status_code == 503
    assert "未配置" in resp.json()["detail"]


def test_ai_draft_success_with_mock(auth_headers, client, db_session, monkeypatch):
    """正常调用（mock AIService.chat 返回固定 JSON）。"""
    from app.models.user import User
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

    # 预置带 STAR 细节的职业事件
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    db_session.add(
        CareerEvent(
            user_id=user.id,
            event_date=date(2025, 6, 1),
            event_type=EventType.project_done,
            title="完成核心系统重构",
            situation="旧系统性能瓶颈严重",
            task="主导重构方案设计与实施",
            action="引入微服务架构并完成迁移",
            result="系统吞吐量提升 3 倍",
        )
    )
    db_session.commit()

    with patch.object(
        ai_service.AIService,
        "chat",
        AsyncMock(return_value=MOCK_RETRO_DRAFT_RESPONSE),
    ):
        resp = client.post(
            "/api/retrospectives/ai-draft",
            headers=auth_headers,
            json=_ai_draft_payload(),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["achievements"]) == 2
    assert "沟通瓶颈" in data["challenges"]
    assert data["suggested_satisfaction"] == 4
    assert len(data["next_steps"]) == 2
    assert "进展顺利" in data["summary"]


def test_ai_draft_empty_period_still_works(auth_headers, client, db_session, monkeypatch):
    """时段内无事件时仍能正常生成草稿。"""
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

    with patch.object(
        ai_service.AIService,
        "chat",
        AsyncMock(return_value=MOCK_RETRO_DRAFT_RESPONSE),
    ):
        resp = client.post(
            "/api/retrospectives/ai-draft",
            headers=auth_headers,
            json=_ai_draft_payload(),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "achievements" in data
    assert "summary" in data
    assert data["suggested_satisfaction"] == 4


def test_ai_draft_timeout_returns_504(auth_headers, client, db_session, monkeypatch):
    """LLM 超时返回 504。"""
    from app.services import ai_service

    monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "fake-key-for-test")

    async def fake_chat(self, system_prompt, user_content, timeout=30):
        raise httpx.TimeoutException("request timed out")

    with patch.object(ai_service.AIService, "chat", fake_chat):
        resp = client.post(
            "/api/retrospectives/ai-draft",
            headers=auth_headers,
            json=_ai_draft_payload(),
        )
    assert resp.status_code == 504
    assert "超时" in resp.json()["detail"]
