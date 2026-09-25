"""外部验证（D9 Phase 2.2）测试——SSRF 闸/立场推进/冲突不覆盖/AI 失败诚实。

对齐拍板测试要求：
- 外部来源与内部来源冲突时不能覆盖原 Evidence（contradict=留痕+另立一行）；
- 无真实来源不得标 VERIFIED（AI 不可用=503 且状态不变）；
- 内网/保留地址 URL 被安全闸拒绝。
"""

import json

from fastapi.testclient import TestClient

from app.services import evidence_verification_service as verification_service


def _auth(client: TestClient, email: str) -> dict:
    payload = {"email": email, "name": "测试用户"}
    payload["password"] = "Test1234" + "!"
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/login", json=payload)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_evidence(client: TestClient, headers: dict) -> str:
    draft = {
        "question": "要不要跨专业考研？",
        "context": None,
        "options": [],
        "constraints": [],
        "desired_outcome": None,
        "hypotheses": [{"statement": "我能在 8 个月内补齐计算机基础", "importance": "critical"}],
        "evidence_needs": [],
        "ai_used": False,
    }
    card = client.post(
        "/api/decision-os/decisions/confirm-draft",
        json={"draft": draft, "destination_type": "postgrad", "confidence": 4},
        headers=headers,
    ).json()
    ev = client.post(
        f"/api/decision-os/hypotheses/{card['hypotheses'][0]['id']}/evidence",
        json={"claim": "目标院校近 5 年复试线 350 上下"},
        headers=headers,
    )
    assert ev.status_code == 201, ev.text
    return ev.json()["id"]


class _FakeAI:
    def __init__(self, verdict: str):
        self._verdict = verdict

    async def chat(self, **kwargs):
        return json.dumps(
            {"verdict": self._verdict, "summary": f"{self._verdict}：外部页面相关内容"},
            ensure_ascii=False,
        )


def _mock_world(monkeypatch, page: str, verdict: str):
    monkeypatch.setattr(verification_service, "_fetch_text", lambda url: page)
    monkeypatch.setattr(verification_service, "AIOrchestrator", lambda *a, **k: _FakeAI(verdict))


def test_ssrf_guard_rejects_private_and_non_http(client: TestClient, auth_headers: dict):
    ev_id = _make_evidence(client, auth_headers)
    for bad_url in (
        "http://127.0.0.1/secret",
        "http://192.168.1.1/admin",
        "http://10.0.0.5/x",
        "http://[::1]/x",
        "ftp://example.com/file",
        "http://localhost/x",
    ):
        resp = client.post(
            f"/api/decision-os/evidence/{ev_id}/external-verify",
            json={"source_url": bad_url},
            headers=auth_headers,
        )
        assert resp.status_code == 422, f"{bad_url} 应被安全闸拒绝（422）"


def test_agree_marks_externally_verified(client: TestClient, auth_headers: dict, monkeypatch):
    ev_id = _make_evidence(client, auth_headers)
    _mock_world(monkeypatch, "目标院校研究生院官网：2025 年复试线 350 分", "agree")

    resp = client.post(
        f"/api/decision-os/evidence/{ev_id}/external-verify",
        json={"source_url": "https://yz.example.edu.cn/notice"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["verdict"] == "agree"
    assert body["changed"] is True
    assert body["evidence"]["verification_status"] == "externally_verified"
    assert body["evidence"]["verification_source"] == "https://yz.example.edu.cn/notice"
    assert body["evidence"]["verified_on"] is not None
    assert body["new_evidence"] is None


def test_contradict_keeps_original_and_adds_external_row(
    client: TestClient, auth_headers: dict, monkeypatch
):
    ev_id = _make_evidence(client, auth_headers)
    _mock_world(monkeypatch, "官方数据：复试线 390 分，与传闻不符", "contradict")

    resp = client.post(
        f"/api/decision-os/evidence/{ev_id}/external-verify",
        json={"source_url": "https://yz.example.edu.cn/notice"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["evidence"]["verification_status"] == "contradicted"
    # 原证据 claim 不被覆盖
    assert body["evidence"]["claim"] == "目标院校近 5 年复试线 350 上下"
    # 新增外部证据行：立场 contradicting、自带来源与验证状态
    new_ev = body["new_evidence"]
    assert new_ev is not None
    assert new_ev["stance"] == "contradicting"
    assert new_ev["verification_status"] == "externally_verified"
    assert new_ev["provider"].startswith("external:")
    assert new_ev["source_url"] == "https://yz.example.edu.cn/notice"


def test_unrelated_changes_nothing(client: TestClient, auth_headers: dict, monkeypatch):
    ev_id = _make_evidence(client, auth_headers)
    _mock_world(
        monkeypatch, "今天天气不错。这篇博客随便写写生活流水账，与复试线毫无关系。", "unrelated"
    )

    resp = client.post(
        f"/api/decision-os/evidence/{ev_id}/external-verify",
        json={"source_url": "https://blog.example.com/post"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["changed"] is False
    assert body["evidence"]["verification_status"] == "internal_unverified"


def test_ai_unavailable_503_no_silent_verify(client: TestClient, auth_headers: dict, monkeypatch):
    """AI 挂掉=503，证据状态绝不被静默改成 VERIFIED。"""
    ev_id = _make_evidence(client, auth_headers)
    monkeypatch.setattr(
        verification_service,
        "_fetch_text",
        lambda url: "某个有实质内容的官方页面正文，包含复试线与招生说明的完整段落内容。",
    )

    class _DeadAI:
        def __init__(self, *a, **k):
            pass

        async def chat(self, **k):
            raise RuntimeError("llm down")

    monkeypatch.setattr(verification_service, "AIOrchestrator", lambda *a, **k: _DeadAI())

    resp = client.post(
        f"/api/decision-os/evidence/{ev_id}/external-verify",
        json={"source_url": "https://yz.example.edu.cn/notice"},
        headers=auth_headers,
    )
    assert resp.status_code == 503


def test_cross_user_external_verify_404(client: TestClient, auth_headers: dict):
    ev_id = _make_evidence(client, auth_headers)
    headers_b = _auth(client, "ev-b@example.com")
    resp = client.post(
        f"/api/decision-os/evidence/{ev_id}/external-verify",
        json={"source_url": "https://yz.example.edu.cn/notice"},
        headers=headers_b,
    )
    assert resp.status_code == 404
