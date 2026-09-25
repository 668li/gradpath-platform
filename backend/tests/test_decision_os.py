"""Decision OS（D9）闭环测试 — 所有权/证据闸/AI 降级/闭环联动。

对齐拍板测试要求：
- 用户 A 不能访问用户 B 的决策/证据/行动（跨用户一律 404）
- 证据创建一律 internal_unverified（内部库 Provider 也不例外）
- externally_verified 无 verification_source = 422（无真实来源不得标 VERIFIED）
- 未知 hypothesis → 404（不存在随机路由）
- 行动只在显式携带 hypothesis_status_update 时改假设状态（系统不替用户决定）
- AI 结构化：LLM 不可用诚实降级，不编造假设凑数
- legacy 兼容：旧决策（无新字段）卡片可读
"""

import json
import uuid

from fastapi.testclient import TestClient


def _fixture_password() -> str:
    """测试夹具口令，与 tests/conftest.py 的 auth_headers 夹具同源；非真实凭据。"""
    return "Test1234" + "!"


DRAFT = {
    "question": "我要不要跨专业考研计算机？",
    "context": "大一，对现专业兴趣不足",
    "options": ["跨考计算机", "考公", "直接就业"],
    "constraints": ["8 个月备考时间"],
    "desired_outcome": "上岸且就业不差",
    "hypotheses": [
        {
            "statement": "我能在 8 个月内补齐计算机基础并达到目标院校要求",
            "importance": "critical",
            "impact": "决策直接崩塌",
        },
        {
            "statement": "计算机就业的长期收益明显高于继续现专业",
            "importance": "high",
            "impact": "收益论证不成立",
        },
    ],
    "evidence_needs": ["目标院校近 5 年复试线"],
    "ai_used": True,
}


def _auth(client: TestClient, email: str) -> dict:
    payload = {"email": email, "name": "测试用户"}
    payload["password"] = _fixture_password()
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/login", json=payload)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _confirm_draft(client: TestClient, headers: dict, draft: dict | None = None) -> dict:
    resp = client.post(
        "/api/decision-os/decisions/confirm-draft",
        json={"draft": draft or DRAFT, "destination_type": "postgrad", "confidence": 4},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_confirm_draft_creates_decision_and_hypotheses(client: TestClient, auth_headers: dict):
    card = _confirm_draft(client, auth_headers)
    assert card["decision"]["question"] == DRAFT["question"]
    assert card["decision"]["status"] == "planned"
    assert len(card["hypotheses"]) == 2
    assert card["hypotheses"][0]["status"] == "untested"
    assert card["hypotheses"][0]["evidence_count"] == 0
    # legacy 镜像：旧视图的 assumptions 可读
    assert card["decision"]["assumptions"] == [h["statement"] for h in DRAFT["hypotheses"]]


def test_evidence_gate_defaults_internal_unverified(client: TestClient, auth_headers: dict):
    card = _confirm_draft(client, auth_headers)
    hyp_id = card["hypotheses"][0]["id"]
    resp = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/evidence",
        json={
            "claim": "目标院校计算机近 5 年复试线 350 上下",
            "provider": "internal:grad_intel",
            "source_type": "internal_db",
            # 客户端试图自带验证状态 —— schema 无此字段，必须被忽略
            "verification_status": "externally_verified",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["verification_status"] == "internal_unverified"
    assert body["verification_source"] is None
    assert body["verified_on"] is None


def test_verify_requires_source_for_external(client: TestClient, auth_headers: dict):
    card = _confirm_draft(client, auth_headers)
    hyp_id = card["hypotheses"][0]["id"]
    ev = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/evidence",
        json={"claim": "某经验贴称跨考需 10 个月", "source_type": "peer"},
        headers=auth_headers,
    ).json()

    # 无来源标 externally_verified = 禁止（422）
    bad = client.post(
        f"/api/decision-os/evidence/{ev['id']}/verify",
        json={"verification_status": "externally_verified"},
        headers=auth_headers,
    )
    assert bad.status_code == 422

    ok = client.post(
        f"/api/decision-os/evidence/{ev['id']}/verify",
        json={
            "verification_status": "externally_verified",
            "verification_source": "目标院校研究生院官网简章",
        },
        headers=auth_headers,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["verification_status"] == "externally_verified"
    assert ok.json()["verified_on"] is not None


def test_cross_user_isolation(client: TestClient, auth_headers: dict):
    """用户 A 不能访问用户 B 的决策/假设/证据/行动。"""
    card_a = _confirm_draft(client, auth_headers)
    decision_id = card_a["decision"]["id"]
    hyp_id = card_a["hypotheses"][0]["id"]

    action = client.post(
        f"/api/decision-os/decisions/{decision_id}/actions",
        json={"title": "采访 3 名跨考上岸学生", "hypothesis_id": hyp_id},
        headers=auth_headers,
    )
    assert action.status_code == 201, action.text
    action_id = action.json()["id"]

    ev = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/evidence",
        json={"claim": "A 的证据"},
        headers=auth_headers,
    ).json()

    headers_b = _auth(client, "user-b@example.com")

    assert (
        client.get(f"/api/decision-os/decisions/{decision_id}/card", headers=headers_b).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/decision-os/hypotheses/{hyp_id}",
            json={"status": "refuted"},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/decision-os/hypotheses/{hyp_id}/evidence",
            json={"claim": "B 的证据"},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/decision-os/actions/{action_id}/complete",
            json={"result": "B 伪造完成", "result_stance": "hypothesis_supported"},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/decision-os/evidence/{ev['id']}", headers=headers_b).status_code == 404
    )


def test_unknown_hypothesis_returns_404_no_routing(client: TestClient, auth_headers: dict):
    """未知 hypothesis 不得随机路由/不静默落库。"""
    resp = client.post(
        f"/api/decision-os/hypotheses/{uuid.uuid4()}/evidence",
        json={"claim": "孤儿证据"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_complete_action_updates_hypothesis_only_when_explicit(
    client: TestClient, auth_headers: dict
):
    card = _confirm_draft(client, auth_headers)
    decision_id = card["decision"]["id"]
    hyp_id = card["hypotheses"][0]["id"]

    action1 = client.post(
        f"/api/decision-os/decisions/{decision_id}/actions",
        json={"title": "查近 5 年复试线", "hypothesis_id": hyp_id},
        headers=auth_headers,
    ).json()
    client.post(
        f"/api/decision-os/actions/{action1['id']}/complete",
        json={"result": "复试线稳定在 350", "result_stance": "hypothesis_supported"},
        headers=auth_headers,
    )
    # 未显式携带 hypothesis_status_update → 假设状态不动（不替用户下结论）
    card_now = client.get(
        f"/api/decision-os/decisions/{decision_id}/card", headers=auth_headers
    ).json()
    assert card_now["hypotheses"][0]["status"] == "untested"

    action2 = client.post(
        f"/api/decision-os/decisions/{decision_id}/actions",
        json={"title": "找 3 名上岸学生聊", "hypothesis_id": hyp_id},
        headers=auth_headers,
    ).json()
    client.post(
        f"/api/decision-os/actions/{action2['id']}/complete",
        json={
            "result": "3 人都说 8 个月够",
            "result_stance": "hypothesis_supported",
            "hypothesis_status_update": "supporting",
        },
        headers=auth_headers,
    )
    card_now = client.get(
        f"/api/decision-os/decisions/{decision_id}/card", headers=auth_headers
    ).json()
    assert card_now["hypotheses"][0]["status"] == "supporting"


def test_action_cannot_link_hypothesis_of_other_decision(client: TestClient, auth_headers: dict):
    card1 = _confirm_draft(client, auth_headers)
    card2 = _confirm_draft(client, auth_headers, draft={**DRAFT, "question": "要不要考公？"})
    resp = client.post(
        f"/api/decision-os/decisions/{card2['decision']['id']}/actions",
        json={"title": "跨决策挂接", "hypothesis_id": card1["hypotheses"][0]["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_card_aggregates_full_loop(client: TestClient, auth_headers: dict):
    card = _confirm_draft(client, auth_headers)
    decision_id = card["decision"]["id"]
    hyp_id = card["hypotheses"][0]["id"]

    client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/evidence",
        json={"claim": "支持", "stance": "supporting"},
        headers=auth_headers,
    )
    client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/evidence",
        json={"claim": "反对", "stance": "contradicting"},
        headers=auth_headers,
    )
    client.post(
        f"/api/decision-os/decisions/{decision_id}/evidence",
        json={"claim": "决策级证据", "provider": "internal:market_data"},
        headers=auth_headers,
    )
    client.post(
        f"/api/decision-os/decisions/{decision_id}/outcomes",
        json={"kind": "partial", "summary": "初试过了，复试待定"},
        headers=auth_headers,
    )
    client.post(
        f"/api/decision-os/decisions/{decision_id}/reflections",
        json={
            "wrong_assumption": "低估了数学难度",
            "lesson": "先做一套真题再立假设",
            "match_status": "partial",
        },
        headers=auth_headers,
    )

    card_now = client.get(
        f"/api/decision-os/decisions/{decision_id}/card", headers=auth_headers
    ).json()
    hyp = next(h for h in card_now["hypotheses"] if h["id"] == hyp_id)
    assert hyp["evidence_count"] == 2
    assert hyp["supporting"] == 1
    assert hyp["contradicting"] == 1
    assert len(card_now["outcomes"]) == 1
    assert card_now["outcomes"][0]["kind"] == "partial"
    assert len(card_now["reflections"]) == 1
    assert card_now["reflections"][0]["lesson"] == "先做一套真题再立假设"


def test_reflection_requires_content(client: TestClient, auth_headers: dict):
    card = _confirm_draft(client, auth_headers)
    resp = client.post(
        f"/api/decision-os/decisions/{card['decision']['id']}/reflections",
        json={},
        headers=auth_headers,
    )
    assert resp.status_code == 422


def test_structure_degrades_without_llm(client: TestClient, auth_headers: dict, monkeypatch):
    """LLM 不可用时诚实降级：ai_used=False、question=原文、不编造假设。"""

    class _BrokenOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, **kwargs):
            raise RuntimeError("llm down")

    monkeypatch.setattr("app.services.decision_os_service.AIOrchestrator", _BrokenOrchestrator)
    raw = "我不知道毕业后应该考研还是直接工作，家里希望我考公"
    resp = client.post("/api/decision-os/structure", json={"raw_text": raw}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ai_used"] is False
    assert body["question"] == raw
    assert body["hypotheses"] == []


def test_structure_parses_llm_json(client: TestClient, auth_headers: dict, monkeypatch):
    payload = {
        "question": "要不要跨专业考研？",
        "context": None,
        "options": ["跨考", "不跨"],
        "constraints": [],
        "desired_outcome": None,
        "hypotheses": [
            {"statement": "我能补齐基础", "importance": "critical", "impact": "崩塌"},
            {"statement": "收益更高", "importance": "bogus"},  # 非法 importance → 保守归 high
        ],
        "evidence_needs": ["近 5 年复试线"],
    }

    class _FakeOrchestrator:
        def __init__(self, *args, **kwargs):
            pass

        async def chat(self, **kwargs):
            return "前置废话 " + json.dumps(payload, ensure_ascii=False) + " 后置废话"

    monkeypatch.setattr("app.services.decision_os_service.AIOrchestrator", _FakeOrchestrator)
    resp = client.post(
        "/api/decision-os/structure",
        json={"raw_text": "要不要跨专业考研？"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ai_used"] is True
    assert body["question"] == "要不要跨专业考研？"
    assert len(body["hypotheses"]) == 2
    assert body["hypotheses"][1]["importance"] == "high"


def test_legacy_decision_card_compatible(client: TestClient, auth_headers: dict):
    """旧入口创建的决策（无 Decision OS 字段）卡片可读，新字段给安全默认。"""
    resp = client.post(
        "/api/decisions",
        json={
            "decision_date": "2026-09-25",
            "destination_type": "employment",
            "confidence": 3,
            "reasoning": "老式创建",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    decision_id = resp.json()["id"]
    card = client.get(f"/api/decision-os/decisions/{decision_id}/card", headers=auth_headers)
    assert card.status_code == 200, card.text
    body = card.json()
    assert body["decision"]["question"] is None
    assert body["decision"]["constraints"] == []
    assert body["hypotheses"] == []
