"""Decision OS action linkage tests."""

def _create_decision(client, auth_headers, statement="学历是关键门槛"):
    resp = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-09-20",
            "destination_type": "postgrad",
            "status": "planned",
            "details": {"target_school": "某大学"},
            "reasoning": "测试行动与决策的关系",
            "confidence": 3,
            "assumptions": [statement],
        },
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_micro_action_plan_can_bind_to_decision(auth_headers, client):
    decision_id = _create_decision(client, auth_headers)

    plan = client.post(
        "/api/micro-actions/plans",
        headers=auth_headers,
        json={
            "target_path": "kaoyan",
            "target_role": "计算机",
            "decision_id": decision_id,
        },
    )
    assert plan.status_code == 201
    body = plan.json()
    assert body["decision_id"] == decision_id
    assert body["tasks"][0]["hypothesis_id"] is None


def test_micro_action_task_can_bind_to_same_decision_hypothesis(auth_headers, client):
    decision_id = _create_decision(client, auth_headers, "目标岗位普遍要求硕士")
    hypotheses = client.get(
        f"/api/decisions/{decision_id}/hypotheses",
        headers=auth_headers,
    )
    hypothesis_id = hypotheses.json()[0]["id"]

    plan = client.post(
        "/api/micro-actions/plans",
        headers=auth_headers,
        json={"target_path": "employment", "decision_id": decision_id},
    )
    task_id = plan.json()["tasks"][0]["id"]

    linked = client.patch(
        f"/api/micro-actions/tasks/{task_id}/hypothesis",
        headers=auth_headers,
        json={"hypothesis_id": hypothesis_id},
    )
    assert linked.status_code == 200
    assert linked.json()["hypothesis_id"] == hypothesis_id


def test_micro_action_task_rejects_cross_decision_hypothesis(auth_headers, client):
    first_decision = _create_decision(client, auth_headers, "第一条决策假设")
    second_decision = _create_decision(client, auth_headers, "第二条决策假设")

    hypotheses = client.get(
        f"/api/decisions/{first_decision}/hypotheses",
        headers=auth_headers,
    )
    hypothesis_id = hypotheses.json()[0]["id"]

    plan = client.post(
        "/api/micro-actions/plans",
        headers=auth_headers,
        json={"target_path": "employment", "decision_id": second_decision},
    )
    task_id = plan.json()["tasks"][0]["id"]

    bad = client.patch(
        f"/api/micro-actions/tasks/{task_id}/hypothesis",
        headers=auth_headers,
        json={"hypothesis_id": hypothesis_id},
    )
    assert bad.status_code == 404
