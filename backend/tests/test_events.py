from datetime import date


def test_create_event(auth_headers, client):
    resp = client.post(
        "/api/events",
        headers=auth_headers,
        json={
            "event_date": "2026-06-01",
            "event_type": "onboard",
            "title": "入职腾讯",
            "description": "后端开发工程师",
            "situation": "校招拿到offer",
            "task": "熟悉业务代码",
            "action": "参加新人培训+结对编程",
            "result": "两周内完成第一个需求",
            "reflection": "应该更主动地与导师沟通",
            "skills_gained": ["Go", "微服务"],
            "mood": 4,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "入职腾讯"
    assert "Go" in data["skills_gained"]
    assert data["reflection"] is not None


def test_list_events_filtered_by_type(auth_headers, client):
    for etype in ["onboard", "promotion", "onboard"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": "2026-06-01",
                "event_type": etype,
                "title": f"事件-{etype}",
                "description": "...",
            },
        )
    resp = client.get("/api/events?event_type=onboard", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 2


def test_list_events_filtered_by_date_range(auth_headers, client):
    for d in ["2026-01-15", "2026-03-20", "2026-06-10"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": d,
                "event_type": "other",
                "title": f"事件-{d}",
                "description": "...",
            },
        )
    resp = client.get(
        "/api/events?start_date=2026-02-01&end_date=2026-05-01",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_update_event(auth_headers, client):
    create = client.post(
        "/api/events",
        headers=auth_headers,
        json={
            "event_date": "2026-06-01",
            "event_type": "skill_acquired",
            "title": "学习Docker",
            "description": "...",
        },
    )
    eid = create.json()["id"]
    resp = client.patch(
        f"/api/events/{eid}",
        headers=auth_headers,
        json={"title": "掌握Docker", "skills_gained": ["Docker", "K8s"]},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "掌握Docker"
    assert "K8s" in resp.json()["skills_gained"]


def test_delete_event(auth_headers, client):
    create = client.post(
        "/api/events",
        headers=auth_headers,
        json={
            "event_date": "2026-06-01",
            "event_type": "other",
            "title": "待删除",
            "description": "...",
        },
    )
    eid = create.json()["id"]
    resp = client.delete(f"/api/events/{eid}", headers=auth_headers)
    assert resp.status_code == 204
