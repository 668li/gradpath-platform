def test_provider_registry_and_routing(client):
    response = client.get("/api/evidence-providers")
    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert {"university", "cutoff", "salary", "company", "recruitment", "civil_service", "employment"} <= names

    routed = client.post(
        "/api/evidence-providers/route",
        json={"hypothesis": "我的考研分数能达到目标院校复试线，而且毕业后薪资可以达到预期"},
    )
    assert routed.status_code == 200
    routed_names = [item["name"] for item in routed.json()["providers"]]
    assert routed_names[:2] == ["cutoff", "salary"]


def test_hypothesis_scoped_provider_discovery_is_user_and_decision_bound(auth_headers, client):
    decision = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-09-20",
            "destination_type": "postgrad",
            "status": "planned",
            "details": {},
            "reasoning": "provider discovery",
            "confidence": 3,
        },
    )
    assert decision.status_code == 201
    decision_id = decision.json()["id"]

    hypothesis = client.post(
        f"/api/decisions/{decision_id}/hypotheses",
        headers=auth_headers,
        json={
            "statement": "我的考研分数能达到目标院校复试线，而且毕业后薪资可以达到预期",
            "importance": 5,
            "confidence": 0.5,
        },
    )
    assert hypothesis.status_code == 201
    hypothesis_id = hypothesis.json()["id"]

    discovered = client.post(
        f"/api/evidence-providers/decisions/{decision_id}/hypotheses/{hypothesis_id}/discover",
        headers=auth_headers,
        json={"hypothesis": hypothesis.json()["statement"], "limit": 2},
    )
    assert discovered.status_code == 200
    payload = discovered.json()
    names = [item["provider"] for item in payload["providers"]]
    assert names[:2] == ["cutoff", "salary"]
    assert payload["verification_policy"] == "internal_unverified_until_external_check"
