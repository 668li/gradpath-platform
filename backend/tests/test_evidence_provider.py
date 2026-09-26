"""Provider Router（D9 Phase 2.1）测试——白名单硬闸/所有权/候选形状。

对齐拍板测试要求：
- AI Provider Router 只能返回白名单 Provider（未知名=404，不随机路由）；
- 未知 Hypothesis 不得路由到任何 Provider（404）；
- 用户 A 不能搜用户 B 的假设；
- 候选≠证据：响应无 verification_status 字段；候选必须带 provider 与溯源。
"""

import uuid

from fastapi.testclient import TestClient

from app.models.experience_post import ExperiencePost
from app.models.grad_intel import GradSchoolIntel, GradScorelineRecord


def _auth(client: TestClient, email: str) -> dict:
    payload = {"email": email, "name": "测试用户"}
    payload["password"] = "Test1234" + "!"
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/login", json=payload)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _make_hypothesis(client: TestClient, headers: dict) -> str:
    """直连既有端点建决策+假设，返回 hypothesis_id。"""

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
    resp = client.post(
        "/api/decision-os/decisions/confirm-draft",
        json={"draft": draft, "destination_type": "postgrad", "confidence": 4},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["hypotheses"][0]["id"]


def test_provider_list_is_whitelist_only(client: TestClient, auth_headers: dict):
    hyp_id = _make_hypothesis(client, auth_headers)
    resp = client.get(f"/api/decision-os/hypotheses/{hyp_id}/providers", headers=auth_headers)
    assert resp.status_code == 200
    names = {p["name"] for p in resp.json()}
    assert names == {
        "grad_school_intel",
        "grad_scoreline",
        "grad_yanzhao",
        "experience_post",
        "employment",
        "market",
    }
    # Q8 拍板：无溯源的 school/company 不进白名单
    assert "school" not in names and "company" not in names


def test_unknown_provider_404_no_random_routing(client: TestClient, auth_headers: dict):
    hyp_id = _make_hypothesis(client, auth_headers)
    for bad in ("school", "company", "dark_knowledge", "nonexistent"):
        resp = client.post(
            f"/api/decision-os/hypotheses/{hyp_id}/providers/{bad}/search",
            json={"query": "计算机"},
            headers=auth_headers,
        )
        assert resp.status_code == 404, f"{bad} 应 404"


def test_unknown_or_foreign_hypothesis_404(client: TestClient, auth_headers: dict):
    # 未知
    resp = client.post(
        f"/api/decision-os/hypotheses/{uuid.uuid4()}/providers/grad_scoreline/search",
        json={"query": "计算机"},
        headers=auth_headers,
    )
    assert resp.status_code == 404

    # 他人
    headers_b = _auth(client, "pr-b@example.com")
    hyp_id = _make_hypothesis(client, auth_headers)
    resp = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/providers/grad_scoreline/search",
        json={"query": "计算机"},
        headers=headers_b,
    )
    assert resp.status_code == 404


def test_scoreline_search_returns_candidates_with_source(
    client: TestClient, auth_headers: dict, db_session
):
    db_session.add(
        GradScorelineRecord(
            university_name="测试大学",
            major_name="计算机科学与技术",
            year=2025,
            total_score_line=350,
            politics_score=60,
            data_sources=["https://yz.chsi.com.cn/test-source"],
        )
    )
    db_session.commit()

    hyp_id = _make_hypothesis(client, auth_headers)
    resp = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/providers/grad_scoreline/search",
        json={"query": "计算机"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    candidates = resp.json()
    assert len(candidates) == 1
    c = candidates[0]
    assert "350" in c["claim"]
    assert c["provider"] == "internal:grad_scoreline"
    assert c["source_url"] == "https://yz.chsi.com.cn/test-source"
    assert c["source_type"] == "internal_db"
    # 候选不是证据：绝不携带验证状态字段
    assert "verification_status" not in c

    # 候选入账走既有证据闸：创建后必须 internal_unverified
    ev = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/evidence",
        json={"claim": c["claim"], "provider": c["provider"], "source_url": c["source_url"]},
        headers=auth_headers,
    )
    assert ev.status_code == 201
    assert ev.json()["verification_status"] == "internal_unverified"


def test_ai_generated_intel_excluded(client: TestClient, auth_headers: dict, db_session):
    """零造假红线：AI 生成情报不出候选。"""
    db_session.add(
        GradSchoolIntel(
            user_id=uuid.uuid4(),
            school_name="AI大学",
            major_name="计算机",
            background_discrimination="友好",
            is_ai_generated=True,
        )
    )
    db_session.add(
        GradSchoolIntel(
            user_id=uuid.uuid4(),
            school_name="真人大学",
            major_name="计算机",
            background_discrimination="歧视双非",
            is_ai_generated=False,
        )
    )
    db_session.commit()

    hyp_id = _make_hypothesis(client, auth_headers)
    resp = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/providers/grad_school_intel/search",
        json={"query": "计算机"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    claims = [c["claim"] for c in resp.json()]
    assert len(claims) == 1
    assert "真人大学" in claims[0]


def test_experience_post_verified_reliability(client: TestClient, auth_headers: dict, db_session):
    db_session.add(
        ExperiencePost(
            user_id=uuid.uuid4(),
            title="跨考计算机 8 个月上岸",
            content="8 个月补齐 408 基础的完整规划",
            status="approved",
            is_verified=True,
            source_platform="zhihu",
        )
    )
    db_session.commit()

    hyp_id = _make_hypothesis(client, auth_headers)
    resp = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/providers/experience_post/search",
        json={"query": "跨考计算机"},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    c = resp.json()[0]
    assert c["source_type"] == "peer"
    assert c["reliability"] == "medium"
    assert c["provider"] == "internal:experience_post"


def test_empty_query_422(client: TestClient, auth_headers: dict):
    hyp_id = _make_hypothesis(client, auth_headers)
    resp = client.post(
        f"/api/decision-os/hypotheses/{hyp_id}/providers/grad_scoreline/search",
        json={"query": ""},
        headers=auth_headers,
    )
    assert resp.status_code == 422
