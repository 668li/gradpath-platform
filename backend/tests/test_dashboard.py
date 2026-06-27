def test_dashboard_empty(auth_headers, client):
    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decisions_count"] == 0
    assert data["events_count"] == 0
    assert data["skills_count"] == 0
    assert data["retrospectives_count"] == 0
    assert data["latest_decision"] is None
    assert data["recent_events"] == []
    assert data["timeline"] == []


def test_dashboard_with_data(auth_headers, client):
    # 创建决策
    client.post(
        "/api/decisions",
        headers=auth_headers,
        json={
            "decision_date": "2026-06-01",
            "destination_type": "employment",
            "status": "confirmed",
            "details": {"company": "腾讯"},
            "reasoning": "...",
            "confidence": 4,
        },
    )
    # 创建事件
    for title in ["入职", "完成项目", "晋升"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": "2026-06-15",
                "event_type": "onboard",
                "title": title,
                "description": "...",
            },
        )
    # 创建技能
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "Python", "category": "后端", "level": 4},
    )

    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["decisions_count"] == 1
    assert data["events_count"] == 3
    assert data["skills_count"] == 1
    assert data["latest_decision"] is not None
    assert len(data["recent_events"]) == 3
    # timeline 合并了决策和事件
    assert len(data["timeline"]) == 4


def test_dashboard_skill_categories(auth_headers, client):
    for cat in ["后端", "后端", "前端"]:
        client.post(
            "/api/skills",
            headers=auth_headers,
            json={"name": f"技能-{cat}", "category": cat, "level": 3},
        )
    resp = client.get("/api/dashboard/overview", headers=auth_headers)
    data = resp.json()
    assert data["skill_categories"]["后端"] == 2
    assert data["skill_categories"]["前端"] == 1
