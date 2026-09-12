"""目标拆解器端点测试（#14）—— 编排器与配额全 mock，不真调 LLM。"""

import json
import uuid
from types import SimpleNamespace

import pytest

from app.api import goal_decompose as gd

CANNED = {
    "steps": [
        {
            "day_number": i,
            "title": f"微行动{i}",
            "description": f"打开材料做第 {i} 小步",
            "minutes": 5,
            "anchor": "坐到书桌前",
            "task_type": "practice",
            "fogg": {"m": 4, "a": 5, "p": 4},
        }
        for i in range(1, 8)
    ],
    "note": "先打开，再缩小",
}


class FakeOrchestrator:
    def __init__(self, payload: str):
        self.payload = payload

    async def chat(self, system_prompt, user_prompt, timeout=30):
        return self.payload


@pytest.fixture
def mock_llm(monkeypatch):
    """安装假编排器 + 假配额（免真实 LLM 与每日限额干扰）。"""

    async def _ok_quota(user_id):
        return None

    async def _noop_incr(user_id):
        return None

    def _install(payload: str):
        monkeypatch.setattr(gd, "AIOrchestrator", lambda: FakeOrchestrator(payload))
        monkeypatch.setattr(gd, "check_llm_quota", _ok_quota)
        monkeypatch.setattr(gd, "incr_llm_quota", _noop_incr)

    return _install


def test_preview_parses_llm_and_normalizes(client, auth_headers, mock_llm):
    mock_llm(json.dumps(CANNED, ensure_ascii=False))
    resp = client.post(
        "/api/goal-decompose/preview",
        json={"goal": "考上浙大计算机研", "path_type": "kaoyan", "motivation": 2},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["steps"]) == 7
    assert data["steps"][0]["day_number"] == 1
    assert data["steps"][0]["estimated_minutes"] <= 15
    assert set(data["steps"][0]["fogg"].keys()) == {"m", "a", "p"}
    assert data["note"]


def test_preview_llm_garbage_returns_502(client, auth_headers, mock_llm):
    mock_llm("抱歉，我无法输出 JSON。")
    resp = client.post(
        "/api/goal-decompose/preview",
        json={"goal": "考上浙大计算机研", "path_type": "kaoyan", "motivation": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 502


def test_preview_rejects_bad_path_type(client, auth_headers):
    resp = client.post(
        "/api/goal-decompose/preview",
        json={"goal": "考上浙大", "path_type": "abroad", "motivation": 3},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_commit_creates_plan(client, auth_headers, monkeypatch):
    captured = {}

    def fake_create_plan(db, user_id, path_type, target_role, tasks):
        captured["path_type"] = path_type
        captured["target_role"] = target_role
        captured["tasks"] = tasks
        return SimpleNamespace(id=uuid.uuid4(), target_role=target_role)

    monkeypatch.setattr(gd, "create_plan_from_tasks", fake_create_plan)
    steps = [
        {
            "day_number": i,
            "title": f"微行动{i}",
            "description": "打开材料做一小步",
            "estimated_minutes": 5,
            "anchor": "坐到书桌前",
            "task_type": "practice",
            "fogg": {"m": 4, "a": 5, "p": 4},
        }
        for i in range(1, 8)
    ]
    resp = client.post(
        "/api/goal-decompose/commit",
        json={"goal": "考上浙大计算机研", "path_type": "kaoyan", "steps": steps},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_count"] == 7
    assert data["redirect"] == "/micro-actions"
    assert captured["path_type"] == "kaoyan"
    assert captured["target_role"] == "考上浙大计算机研"
    # 天数映射到既有微行动 7 天结构
    assert [t["day_number"] for t in captured["tasks"]] == list(range(1, 8))


def test_commit_rejects_too_few_steps(client, auth_headers):
    resp = client.post(
        "/api/goal-decompose/commit",
        json={
            "goal": "考上浙大",
            "path_type": "kaoyan",
            "steps": [{"day_number": 1, "title": "x", "description": "y"}],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 422
