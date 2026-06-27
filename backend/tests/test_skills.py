def test_create_skill(auth_headers, client):
    resp = client.post(
        "/api/skills",
        headers=auth_headers,
        json={
            "name": "Python",
            "category": "后端",
            "level": 4,
            "acquired_date": "2024-09-01",
            "notes": "主力语言",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["name"] == "Python"
    assert resp.json()["level"] == 4


def test_skill_tree_with_parent(auth_headers, client):
    parent = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "后端开发", "category": "后端", "level": 4},
    )
    pid = parent.json()["id"]
    child = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "FastAPI", "category": "后端", "level": 3, "parent_id": pid},
    )
    assert child.status_code == 201
    assert child.json()["parent_id"] == pid


def test_get_skill_tree(auth_headers, client):
    root = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "前端", "category": "前端", "level": 3},
    )
    rid = root.json()["id"]
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "React", "category": "前端", "level": 4, "parent_id": rid},
    )
    client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "Vue", "category": "前端", "level": 3, "parent_id": rid},
    )
    resp = client.get("/api/skills", headers=auth_headers)
    assert resp.status_code == 200
    tree = resp.json()
    assert len(tree) == 1  # 只有一个根节点
    assert len(tree[0]["children"]) == 2


def test_skill_stats(auth_headers, client):
    for cat in ["后端", "后端", "前端", "软技能"]:
        client.post(
            "/api/skills",
            headers=auth_headers,
            json={"name": f"技能-{cat}", "category": cat, "level": 3},
        )
    resp = client.get("/api/skills/stats", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["后端"] == 2
    assert data["前端"] == 1
    assert data["软技能"] == 1


def test_delete_skill(auth_headers, client):
    create = client.post(
        "/api/skills",
        headers=auth_headers,
        json={"name": "待删", "category": "其他", "level": 1},
    )
    sid = create.json()["id"]
    resp = client.delete(f"/api/skills/{sid}", headers=auth_headers)
    assert resp.status_code == 204
