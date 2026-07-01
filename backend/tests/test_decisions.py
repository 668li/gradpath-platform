def test_create_decision_employment(auth_headers, client):
    resp = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "employment",
            "status": "planned",
            "details": {
                "company": "腾讯",
                "position": "后端开发",
                "city": "深圳",
                "salary_range": "25-30k",
                "company_nature": "民企",
            },
            "reasoning": "大厂平台好，技术成长快",
            "confidence": 4,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["destination_type"] == "employment"
    assert data["details"]["company"] == "腾讯"
    assert data["confidence"] == 4


def test_create_decision_postgrad(auth_headers, client):
    resp = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "postgrad",
            "status": "planned",
            "details": {"target_school": "清华大学", "target_major": "计算机", "result": "pending"},
            "reasoning": "想深造",
            "confidence": 3,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["destination_type"] == "postgrad"


def test_list_decisions(auth_headers, client):
    for dtype in ["employment", "abroad", "civil_service"]:
        client.post(
            "/api/decisions",
            headers=auth_headers,
            json={
                "decision_date": "2026-06-27",
                "destination_type": dtype,
                "status": "planned",
                "details": {},
                "reasoning": "...",
                "confidence": 3,
            },
        )
    resp = client.get("/api/decisions", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3


def test_get_decision_by_id(auth_headers, client):
    create = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "phd",
            "status": "planned",
            "details": {"school": "北大", "advisor": "张教授", "field": "AI"},
            "reasoning": "走学术路线",
            "confidence": 5,
        },
    )
    did = create.json()["id"]
    resp = client.get(f"/api/decisions/{did}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == did


def test_update_decision(auth_headers, client):
    create = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "employment",
            "status": "planned",
            "details": {"company": "A公司"},
            "reasoning": "...",
            "confidence": 3,
        },
    )
    did = create.json()["id"]
    resp = client.patch(
        f"/api/decisions/{did}",
        headers=auth_headers,
        json={"status": "confirmed", "confidence": 5},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"
    assert resp.json()["confidence"] == 5


def test_delete_decision(auth_headers, client):
    create = client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-27",
            "destination_type": "gap_year",
            "status": "planned",
            "details": {"plan": "旅行"},
            "reasoning": "...",
            "confidence": 2,
        },
    )
    did = create.json()["id"]
    resp = client.delete(f"/api/decisions/{did}", headers=auth_headers)
    assert resp.status_code == 204
    resp = client.get(f"/api/decisions/{did}", headers=auth_headers)
    assert resp.status_code == 404


def test_decision_stats(auth_headers, client):
    for dtype in ["employment", "employment", "postgrad", "abroad"]:
        client.post(
            "/api/decisions",
            headers=auth_headers,
            json={
                "decision_date": "2026-06-27",
                "destination_type": dtype,
                "status": "planned",
                "details": {},
                "reasoning": "...",
                "confidence": 3,
            },
        )
    resp = client.get("/api/decisions/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["employment"] == 2
    assert data["postgrad"] == 1
    assert data["abroad"] == 1


def test_decision_unauthorized(client):
    resp = client.get("/api/decisions")
    assert resp.status_code == 401
