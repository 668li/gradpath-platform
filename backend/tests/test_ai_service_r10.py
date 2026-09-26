# backend/tests/test_ai_service_r10.py
"""R-10（spec 011 信任对齐第一批）：LLM 上游错误留痕。

- 上游 4xx 时日志与异常消息包含响应体关键字（如 Arrearage），不再伪装成参数错
- chat API 把上游 401/402/403 与其他上游错误分流为 502 两类可区分提示，不再裸 500
"""

import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_service import AIService

# 测试桩 key 运行时随机生成（仅用于本地 FakeClient，不出网，非真实凭据）
_TEST_KEY = "test-" + uuid.uuid4().hex


class _FakeResp:
    """最小上游响应桩：400 + Arrearage 响应体。"""

    status_code = 400
    text = '{"error":{"code":"Arrearage","message":"账户欠费"}}'
    request = httpx.Request("POST", "https://fake.internal/chat/completions")

    def json(self):  # pragma: no cover - 4xx 分支不会走到
        return {}

    def raise_for_status(self):  # pragma: no cover
        return None


class _FakeClient:
    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, *args, **kwargs):
        return _FakeResp()


@pytest.mark.asyncio
async def test_upstream_body_reaches_log_and_exception(monkeypatch, caplog):
    """上游 400+响应体：异常消息与日志都含 Arrearage（R-10 核心）。"""
    monkeypatch.setattr("app.services.ai_service.httpx.AsyncClient", _FakeClient)
    svc = AIService(api_key=_TEST_KEY, model="test-model", base_url="https://fake.internal")

    import logging

    with caplog.at_level(logging.ERROR, logger="gradpath.ai_service"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await svc.chat("sys", "hi")

    assert "Arrearage" in str(exc_info.value)
    assert any("Arrearage" in r.message for r in caplog.records)


def _auth_headers(client: TestClient) -> dict:
    client.post(
        "/api/auth/register",
        json={"email": "r10-probe@example.com", "password": "Test1234!", "name": "r10"},
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "r10-probe@example.com", "password": "Test1234!"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_chat_upstream_4xx_not_bare_500(client: TestClient, monkeypatch):
    """上游 402（欠费类）经 chat API 返回 502 账户/配置提示，而非裸 500。"""
    from app.services import ai_orchestrator as orch_module

    headers = _auth_headers(client)
    created = client.post(
        "/api/chat/conversations",
        json={"title": "r10"},
        headers=headers,
    )
    assert created.status_code in (200, 201), created.text
    conv_id = created.json()["id"]

    class _FakeUpstreamAIService:
        """顶替 AIOrchestrator 内部实例化的 AIService，chat 直接抛上游 402。"""

        def __init__(self, *a, **k):
            pass

        async def chat(self, *a, **k):
            raise httpx.HTTPStatusError(
                "LLM upstream HTTP 402: Arrearage",
                request=httpx.Request("POST", "https://fake.internal"),
                response=httpx.Response(402, text="Arrearage"),
            )

    monkeypatch.setattr(orch_module, "AIService", _FakeUpstreamAIService)
    resp = client.post(
        f"/api/chat/conversations/{conv_id}/messages",
        json={"content": "你好"},
        headers=headers,
    )
    assert resp.status_code == 502, resp.text
    assert "账户或配置" in resp.json()["detail"]
