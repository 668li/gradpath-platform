"""Tests for the first Decision OS evidence-loop slice.

覆盖：
- 创建/读取/更新/删除 hypothesis
- evidence 必须绑定到当前用户的 decision
- evidence 必须引用同一 decision 下的 hypothesis
- readiness 明确区分“有决策”与“有证据”，不伪造准确率
"""

def _create_decision(client, auth_headers):
    resp = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-09-20",
            "destination_type": "postgrad",
            "status": "planned",
            "details": {"target_school": "某大学", "target_major": "计算机"},
            "reasoning": "验证考研是否值得",
            "confidence": 3,
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_hypothesis_crud_and_readiness(auth_headers, client):
    decision_id = _create_decision(client, auth_headers)

    create = client.post(
        f"/api/decisions/{decision_id}/hypotheses",
        headers=auth_headers,
        json={
            "statement": "硕士学历会明显改善目标研发岗的简历筛选",
            "importance": 5,
            "confidence": 0.6,
            "verification_question": "目标岗位中有多少明确要求硕士？",
            "validation_action": "分析 20 个目标岗位",
        },
    )
    assert create.status_code == 201
    hypothesis = create.json()
    assert hypothesis["decision_id"] == decision_id
    assert hypothesis["status"] == "open"

    listing = client.get(
        f"/api/decisions/{decision_id}/hypotheses",
        headers=auth_headers,
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    readiness = client.get(
        f"/api/decisions/{decision_id}/evidence-readiness",
        headers=auth_headers,
    )
    assert readiness.status_code == 200
    data = readiness.json()
    assert data["hypotheses_total"] == 1
    assert data["hypotheses_with_evidence"] == 0
    assert data["hypotheses_unverified"] == 1
    assert data["coverage"] == 0

    update = client.patch(
        f"/api/decisions/{decision_id}/hypotheses/{hypothesis['id']}",
        headers=auth_headers,
        json={"confidence": 0.8, "status": "validated"},
    )
    assert update.status_code == 200
    assert update.json()["confidence"] == 0.8
    assert update.json()["status"] == "validated"

    remove = client.delete(
        f"/api/decisions/{decision_id}/hypotheses/{hypothesis['id']}",
        headers=auth_headers,
    )
    assert remove.status_code == 204


def test_evidence_binds_to_hypothesis_and_changes_readiness(auth_headers, client):
    decision_id = _create_decision(client, auth_headers)
    h = client.post(
        f"/api/decisions/{decision_id}/hypotheses",
        headers=auth_headers,
        json={
            "statement": "目标岗位普遍要求硕士学历",
            "importance": 5,
            "confidence": 0.5,
        },
    )
    hypothesis_id = h.json()["id"]

    evidence = client.post(
        f"/api/decisions/{decision_id}/evidence",
        headers=auth_headers,
        json={
            "hypothesis_id": hypothesis_id,
            "title": "目标岗位学历要求样本",
            "claim": "20 个目标研发岗位中，12 个明确写明硕士优先或硕士及以上",
            "source_type": "dataset",
            "reliability": 4,
            "stance": "supports",
            "excerpt": "学历要求：硕士及以上",
        },
    )
    assert evidence.status_code == 201
    assert evidence.json()["hypothesis_id"] == hypothesis_id

    listing = client.get(
        f"/api/decisions/{decision_id}/evidence?hypothesis_id={hypothesis_id}",
        headers=auth_headers,
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    readiness = client.get(
        f"/api/decisions/{decision_id}/evidence-readiness",
        headers=auth_headers,
    )
    data = readiness.json()
    assert data["evidence_total"] == 1
    assert data["evidence_supporting"] == 1
    assert data["hypotheses_with_evidence"] == 1
    assert data["hypotheses_unverified"] == 0
    assert data["coverage"] == 1


def test_evidence_cannot_cross_link_another_decision(auth_headers, client):
    first_id = _create_decision(client, auth_headers)
    second_id = _create_decision(client, auth_headers)

    h = client.post(
        f"/api/decisions/{first_id}/hypotheses",
        headers=auth_headers,
        json={"statement": "第一条决策假设", "importance": 3, "confidence": 0.5},
    )
    hypothesis_id = h.json()["id"]

    bad = client.post(
        f"/api/decisions/{second_id}/evidence",
        headers=auth_headers,
        json={
            "hypothesis_id": hypothesis_id,
            "title": "越界证据",
            "claim": "不应该被接受",
            "source_type": "user",
            "reliability": 1,
            "stance": "neutral",
        },
    )
    assert bad.status_code == 404

def test_legacy_assumptions_are_bridged_into_hypotheses(auth_headers, client):
    resp = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-09-20",
            "destination_type": "postgrad",
            "status": "planned",
            "details": {},
            "reasoning": "验证旧决策数据兼容性",
            "confidence": 4,
            "assumptions": [
                "学历是目标岗位的主要门槛",
                "我能承担一年备考机会成本",
                "学历是目标岗位的主要门槛",
            ],
        },
    )
    assert resp.status_code == 201
    decision_id = resp.json()["id"]

    hypotheses = client.get(
        f"/api/decisions/{decision_id}/hypotheses",
        headers=auth_headers,
    )
    assert hypotheses.status_code == 200
    items = hypotheses.json()
    assert len(items) == 2
    assert {item["statement"] for item in items} == {
        "学历是目标岗位的主要门槛",
        "我能承担一年备考机会成本",
    }


def test_path_engine_evidence_provider_imports_and_deduplicates(auth_headers, client, monkeypatch):
    decision_id = _create_decision(client, auth_headers)
    hypotheses = client.get(
        f"/api/decisions/{decision_id}/hypotheses",
        headers=auth_headers,
    ).json()
    hypothesis_id = hypotheses[0]["id"]

    def fake_generate_decision(**kwargs):
        assert kwargs["major"] == "计算机"
        return {
            "metrics": [
                {
                    "path_type": "employment",
                    "target_role": "直接就业",
                    "evidence": [
                        {
                            "label": "招聘学历样本",
                            "value": "20 个样本中 12 个岗位明确要求硕士",
                            "source_url": "https://example.com/source",
                            "note": "测试溯源",
                        },
                    ],
                }
            ]
        }

    monkeypatch.setattr(
        "app.services.path_decision_engine.generate_decision",
        fake_generate_decision,
    )

    payload = {
        "major": "计算机",
        "region": "山东",
        "school_tier": "普通",
        "hypothesis_id": hypothesis_id,
    }
    first = client.post(
        f"/api/decisions/{decision_id}/evidence/import-path-engine",
        headers=auth_headers,
        json=payload,
    )
    assert first.status_code == 200
    assert first.json()["imported"] == 1
    assert first.json()["skipped_duplicates"] == 0

    second = client.post(
        f"/api/decisions/{decision_id}/evidence/import-path-engine",
        headers=auth_headers,
        json=payload,
    )
    assert second.status_code == 200
    assert second.json()["imported"] == 0
    assert second.json()["skipped_duplicates"] == 1

    evidence = client.get(
        f"/api/decisions/{decision_id}/evidence",
        headers=auth_headers,
    )
    rows = evidence.json()
    assert len(rows) == 1
    assert rows[0]["source_type"] == "dataset"
    assert rows[0]["reliability"] == 5
    assert rows[0]["hypothesis_id"] == hypothesis_id
