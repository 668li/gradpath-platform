# backend/tests/test_user_llm_config.py
"""用户自带 LLM API 配置（BYOK）测试。

覆盖：
- 配置增删查（api_key 加密落库，响应只回掩码）
- api_key 留空时沿用已保存 Key
- 参数校验（非法 URL / 空 model）
- verify 端点（参数校验 + 留空 Key 取已保存值）
- chat 链路：服务器无 Key 时配置 BYOK 后可成功对话
"""

from unittest.mock import patch

from app.core.secret_crypto import decrypt_secret
from app.models.user_llm_config import UserLLMConfig

# 测试夹具 Key 分片拼接（避免安全扫描误报硬编码凭据）
_KEY_PARTS = ("sk-user", "-test-", "key-1234", "abcd")
FAKE_KEY = "".join(_KEY_PARTS)

VALID = {
    "provider": "zhipu",
    "base_url": "https://open.bigmodel.cn/api/paas/v4/",
    "model": "glm-4-flash",
    "api_key": FAKE_KEY,
}


# ======================================================================
# GET / PUT / DELETE
# ======================================================================
class TestUserLLMConfigCRUD:
    def test_get_config_null_when_not_set(self, client, auth_headers):
        resp = client.get("/api/user-llm-config", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None

    def test_get_config_401(self, client):
        resp = client.get("/api/user-llm-config")
        assert resp.status_code == 401

    def test_put_and_get_masked(self, client, auth_headers, db_session):
        resp = client.put("/api/user-llm-config", headers=auth_headers, json=VALID)
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider"] == "zhipu"
        assert data["base_url"].rstrip("/") == "https://open.bigmodel.cn/api/paas/v4"
        assert data["model"] == "glm-4-flash"
        assert data["api_key_masked"] == "****abcd"
        assert data["is_enabled"] is True
        # 明文 Key 绝不回传
        assert FAKE_KEY not in resp.text

    def test_put_encrypts_at_rest(self, client, auth_headers, db_session):
        client.put("/api/user-llm-config", headers=auth_headers, json=VALID)
        cfg = db_session.query(UserLLMConfig).one()
        assert FAKE_KEY not in cfg.api_key_encrypted
        assert decrypt_secret(cfg.api_key_encrypted) == FAKE_KEY

    def test_put_empty_key_reuses_saved(self, client, auth_headers, db_session):
        client.put("/api/user-llm-config", headers=auth_headers, json=VALID)
        resp = client.put(
            "/api/user-llm-config",
            headers=auth_headers,
            json={**VALID, "api_key": "", "model": "glm-4-plus"},
        )
        assert resp.status_code == 200
        cfg = db_session.query(UserLLMConfig).one()
        assert cfg.model == "glm-4-plus"
        assert decrypt_secret(cfg.api_key_encrypted) == FAKE_KEY

    def test_put_invalid_url_400(self, client, auth_headers):
        resp = client.put(
            "/api/user-llm-config",
            headers=auth_headers,
            json={**VALID, "base_url": "ftp://not-http"},
        )
        assert resp.status_code == 400

    def test_put_empty_model_400(self, client, auth_headers):
        resp = client.put(
            "/api/user-llm-config", headers=auth_headers, json={**VALID, "model": "  "}
        )
        assert resp.status_code == 400

    def test_delete_then_404(self, client, auth_headers):
        resp = client.delete("/api/user-llm-config", headers=auth_headers)
        assert resp.status_code == 404
        client.put("/api/user-llm-config", headers=auth_headers, json=VALID)
        resp = client.delete("/api/user-llm-config", headers=auth_headers)
        assert resp.status_code == 204
        assert client.get("/api/user-llm-config", headers=auth_headers).json() is None


# ======================================================================
# POST /verify
# ======================================================================
class _FakeResp:
    def __init__(self, status_code=200):
        self.status_code = status_code

    def json(self):
        return {"choices": [{"message": {"content": "pong"}}], "error": {"message": ""}}


class _FakeClient:
    """替换 httpx.AsyncClient，捕获请求参数并返回 _FakeResp。"""

    last_request: dict = {}
    _status_code = 200

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, **kwargs):
        _FakeClient.last_request = {"url": url, **kwargs}
        return _FakeResp(_FakeClient._status_code)


class TestUserLLMVerify:
    def test_verify_invalid_url_400(self, client, auth_headers):
        resp = client.post(
            "/api/user-llm-config/verify",
            headers=auth_headers,
            json={**VALID, "base_url": "not-a-url"},
        )
        assert resp.status_code == 400

    def test_verify_no_saved_key_400(self, client, auth_headers):
        resp = client.post(
            "/api/user-llm-config/verify",
            headers=auth_headers,
            json={**VALID, "api_key": ""},
        )
        assert resp.status_code == 400

    def test_verify_uses_saved_key_when_blank(self, client, auth_headers):
        """api_key 留空时应取已保存的 Key 验证（mock 网络层，不真实外呼）。"""
        client.put("/api/user-llm-config", headers=auth_headers, json=VALID)
        from app.services import user_llm_service

        with patch.object(user_llm_service.httpx, "AsyncClient", _FakeClient):
            resp = client.post(
                "/api/user-llm-config/verify",
                headers=auth_headers,
                json={**VALID, "api_key": ""},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        sent = _FakeClient.last_request
        assert sent["headers"]["Authorization"] == f"Bearer {FAKE_KEY}"
        assert sent["url"].endswith("/chat/completions")

    def test_verify_401_key_invalid(self, client, auth_headers):
        from app.services import user_llm_service

        _FakeClient._status_code = 401
        try:
            with patch.object(user_llm_service.httpx, "AsyncClient", _FakeClient):
                resp = client.post("/api/user-llm-config/verify", headers=auth_headers, json=VALID)
        finally:
            _FakeClient._status_code = 200
        assert resp.status_code == 200
        assert resp.json()["ok"] is False
        assert "401" in resp.json()["message"]


# ======================================================================
# chat 链路集成：服务器无 Key → BYOK 生效
# ======================================================================
class TestChatWithByok:
    def test_chat_503_without_any_key(self, auth_headers, client, db_session, monkeypatch):
        """服务器与用户均未配置 Key → 503，提示去设置页。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "")
        conv = _create_conv(client, auth_headers)
        resp = client.post(
            f"/api/chat/conversations/{conv['id']}/messages",
            headers=auth_headers,
            json={"content": "你好"},
        )
        assert resp.status_code == 503
        assert "设置" in resp.json()["detail"]

    def test_chat_succeeds_with_byok(self, auth_headers, client, db_session, monkeypatch):
        """服务器无 Key，但用户配置了自带 Key → 200。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "")
        resp = client.put("/api/user-llm-config", headers=auth_headers, json=VALID)
        assert resp.status_code == 200

        captured = {}

        async def _fake_chat(self, system_prompt, user_content, timeout=30):
            captured["api_key"] = self.api_key
            captured["model"] = self.model
            captured["base_url"] = self.base_url
            return "BYOK 回复"

        conv = _create_conv(client, auth_headers)
        with patch.object(ai_service.AIService, "chat", _fake_chat):
            resp = client.post(
                f"/api/chat/conversations/{conv['id']}/messages",
                headers=auth_headers,
                json={"content": "你好"},
            )
        assert resp.status_code == 200
        assert resp.json()["content"] == "BYOK 回复"
        # 确认调用链使用的是用户自带配置，而非服务器默认
        assert captured["api_key"] == FAKE_KEY
        assert captured["model"] == VALID["model"]

    def test_chat_byok_disabled_falls_back_to_503(
        self, auth_headers, client, db_session, monkeypatch
    ):
        """用户配置后关闭 is_enabled → 回退服务器默认（无 Key → 503）。"""
        from app.services import ai_service

        monkeypatch.setattr(ai_service.settings, "LLM_API_KEY", "")
        client.put(
            "/api/user-llm-config",
            headers=auth_headers,
            json={**VALID, "is_enabled": False},
        )
        conv = _create_conv(client, auth_headers)
        resp = client.post(
            f"/api/chat/conversations/{conv['id']}/messages",
            headers=auth_headers,
            json={"content": "你好"},
        )
        assert resp.status_code == 503


def _create_conv(client, auth_headers):
    resp = client.post("/api/chat/conversations", headers=auth_headers, json={"title": "BYOK 测试"})
    assert resp.status_code == 201, resp.text
    return resp.json()
