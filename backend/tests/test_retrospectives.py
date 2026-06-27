def test_create_retrospective(auth_headers, client):
    resp = client.post(
        "/api/retrospectives",
        headers=auth_headers,
        json={
            "period_type": "annual",
            "period_start": "2025-01-01",
            "period_end": "2025-12-31",
            "title": "2025年度复盘",
            "achievements": ["晋升P6", "主导核心项目"],
            "challenges": "跨团队协作困难",
            "lessons_learned": "沟通需要更前置",
            "next_steps": ["提升架构能力", "拓展技术视野"],
            "satisfaction": 4,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "2025年度复盘"
    assert len(data["achievements"]) == 2
    assert data["satisfaction"] == 4


def test_list_retrospectives(auth_headers, client):
    for i in range(3):
        client.post(
            "/api/retrospectives",
            headers=auth_headers,
            json={
                "period_type": "quarterly",
                "period_start": "2025-01-01",
                "period_end": "2025-03-31",
                "title": f"Q{i+1}复盘",
                "achievements": [],
                "challenges": "...",
                "lessons_learned": "...",
                "next_steps": [],
                "satisfaction": 3,
            },
        )
    resp = client.get("/api/retrospectives", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 3


def test_retrospective_draft(auth_headers, client):
    # 创建几个事件
    for title in ["完成A项目", "获得PMP证书", "晋升"]:
        client.post(
            "/api/events",
            headers=auth_headers,
            json={
                "event_date": "2025-06-15",
                "event_type": "project_done",
                "title": title,
                "description": "...",
            },
        )
    resp = client.get(
        "/api/retrospectives/draft?period_start=2025-01-01&period_end=2025-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["event_summaries"]) == 3
    assert "完成A项目" in [e["title"] for e in data["event_summaries"]]


def test_update_retrospective(auth_headers, client):
    create = client.post(
        "/api/retrospectives",
        headers=auth_headers,
        json={
            "period_type": "custom",
            "period_start": "2025-01-01",
            "period_end": "2025-06-30",
            "title": "半年复盘",
            "achievements": [],
            "challenges": "",
            "lessons_learned": "",
            "next_steps": [],
            "satisfaction": 3,
        },
    )
    rid = create.json()["id"]
    resp = client.patch(
        f"/api/retrospectives/{rid}",
        headers=auth_headers,
        json={"satisfaction": 5, "achievements": ["新成就"]},
    )
    assert resp.status_code == 200
    assert resp.json()["satisfaction"] == 5
    assert resp.json()["achievements"] == ["新成就"]
