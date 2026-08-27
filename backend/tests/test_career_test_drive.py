# backend/tests/test_career_test_drive.py
"""职业试驾 (career-test-drive) 接口测试。

覆盖：认证要求、6 种路径生成、历史记录、单条详情、跨用户隔离。
LLM 未配置时回退到预设模板，测试始终返回有效内容。
"""

import pytest

# 6 种路径 × 目标角色（与 service 中的 6 个模板对应）
PATH_CASES = [
    ("kaoyan", "考研计算机"),
    ("kaoyan", "考研文科"),
    ("employment", "互联网产品经理"),
    ("employment", "软件开发"),
    ("civil_service", "考公基层"),
    ("civil_service", "考公机关"),
]


def test_generate_requires_auth(client):
    """未登录生成应返回 401。"""
    resp = client.post(
        "/api/career-test-drive/generate",
        json={"path_type": "employment", "target_role": "软件开发"},
    )
    assert resp.status_code == 401


def test_history_requires_auth(client):
    """未登录获取历史应返回 401。"""
    resp = client.get("/api/career-test-drive/history")
    assert resp.status_code == 401


def test_get_by_id_requires_auth(client):
    """未登录获取详情应返回 401。"""
    resp = client.get("/api/career-test-drive/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 401


@pytest.mark.parametrize("path_type,target_role", PATH_CASES)
def test_generate_six_paths(auth_headers, client, path_type, target_role):
    """6 种路径生成均返回有效内容。"""
    resp = client.post(
        "/api/career-test-drive/generate",
        headers=auth_headers,
        json={"path_type": path_type, "target_role": target_role},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["path_type"] == path_type
    assert data["target_role"] == target_role
    # 时间段：8-10 个
    blocks = data["experience_content"]
    assert isinstance(blocks, list)
    assert 8 <= len(blocks) <= 10
    for b in blocks:
        assert b["time"]
        assert b["activity"]
        assert b["description"]
        assert b["emotion"]
    # 总结 / 优点 / 挑战
    assert data["summary"]
    assert isinstance(data["pros"], list) and len(data["pros"]) >= 1
    assert isinstance(data["cons"], list) and len(data["cons"]) >= 1
    assert data["id"]
    assert data["created_at"]


def test_history(auth_headers, client):
    """生成 3 条后历史应返回 3 条，按创建时间倒序。"""
    for path_type, target_role in PATH_CASES[:3]:
        client.post(
            "/api/career-test-drive/generate",
            headers=auth_headers,
            json={"path_type": path_type, "target_role": target_role},
        )
    resp = client.get("/api/career-test-drive/history", headers=auth_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 3
    # 倒序：最新的 created_at 应不早于上一条
    for i in range(1, len(items)):
        assert items[i - 1]["created_at"] >= items[i]["created_at"]


def test_get_drive_by_id(auth_headers, client):
    """生成后按 id 查询详情应一致。"""
    create = client.post(
        "/api/career-test-drive/generate",
        headers=auth_headers,
        json={"path_type": "kaoyan", "target_role": "考研计算机"},
    )
    assert create.status_code == 200
    drive_id = create.json()["id"]

    resp = client.get(f"/api/career-test-drive/{drive_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == drive_id
    assert data["target_role"] == "考研计算机"
    assert len(data["experience_content"]) >= 8


def test_get_drive_not_found(auth_headers, client):
    """查询不存在的 id 应返回 404。"""
    resp = client.get(
        "/api/career-test-drive/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_generate_invalid_target_role(auth_headers, client):
    """target_role 为空应被 schema 拒绝（422）。"""
    resp = client.post(
        "/api/career-test-drive/generate",
        headers=auth_headers,
        json={"path_type": "employment", "target_role": ""},
    )
    assert resp.status_code == 422


def test_user_isolation(auth_headers, client):
    """不同用户间试驾记录隔离：另一用户读不到他人记录。"""
    create = client.post(
        "/api/career-test-drive/generate",
        headers=auth_headers,
        json={"path_type": "civil_service", "target_role": "考公机关"},
    )
    drive_id = create.json()["id"]

    # 注册第二个用户
    client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "password": "Test1234!", "name": "另一用户"},
    )
    resp2 = client.post(
        "/api/auth/login",
        json={"email": "other@example.com", "password": "Test1234!"},
    )
    other_headers = {"Authorization": f"Bearer {resp2.json()['access_token']}"}

    # 另一用户读不到该记录
    resp = client.get(f"/api/career-test-drive/{drive_id}", headers=other_headers)
    assert resp.status_code == 404
    # 另一用户的历史应为空
    resp = client.get("/api/career-test-drive/history", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json() == []
