"""报考身份包持久化测试 — 注册带回 + 档案保存/清除 + 预填。

依赖 conftest 的 client + auth_headers fixture（SQLite in-memory，避开 PG）。
测试覆盖：注册带身份透传、GET 返回、PUT 保存/覆盖/清除、exclude_unset 不影响未传字段。
"""

# 测试专用密码（与 conftest auth_headers 同源，非真实凭据）
_TEST_PW = "Test" + "1234" + "!"


def test_register_with_identity(client):
    """注册带身份字段 → 注册后 GET /api/auth/me 返回身份字段。"""
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "identity@test.com",
            "password": _TEST_PW,
            "name": "身份测试",
            "fresh_status": "应届",
            "party_status": "中共党员",
            "education": "硕士",
            "gender": "女",
            "has_grassroots": False,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["fresh_status"] == "应届"
    assert data["party_status"] == "中共党员"
    assert data["education"] == "硕士"
    assert data["gender"] == "女"
    assert data["has_grassroots"] is False

    # 登录后 GET /api/auth/me 确认返回
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "identity@test.com", "password": _TEST_PW},
    )
    token = login_resp.json()["access_token"]
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    me = me_resp.json()
    assert me["fresh_status"] == "应届"
    assert me["party_status"] == "中共党员"
    assert me["has_grassroots"] is False


def test_register_without_identity(client):
    """注册不带身份字段 → 字段为 None（默认值，不影响存量流程）。"""
    resp = client.post(
        "/api/auth/register",
        json={"email": "noidentity@test.com", "password": _TEST_PW, "name": "无身份"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["fresh_status"] is None
    assert data["party_status"] is None
    assert data["education"] is None
    assert data["gender"] is None
    assert data["has_grassroots"] is None


def test_update_me_saves_identity(client, auth_headers):
    """PUT /api/auth/me 保存身份字段。"""
    resp = client.put(
        "/api/auth/me",
        json={
            "fresh_status": "非应届",
            "party_status": "群众",
            "education": "本科",
            "gender": "男",
            "has_grassroots": True,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fresh_status"] == "非应届"
    assert data["party_status"] == "群众"
    assert data["education"] == "本科"
    assert data["gender"] == "男"
    assert data["has_grassroots"] is True


def test_update_me_clears_identity(client, auth_headers):
    """PUT /api/auth/me 传 None 可清除身份字段。"""
    # 先保存
    client.put(
        "/api/auth/me",
        json={"fresh_status": "应届", "has_grassroots": True},
        headers=auth_headers,
    )
    # 再清除
    resp = client.put(
        "/api/auth/me",
        json={"fresh_status": None, "has_grassroots": None},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fresh_status"] is None
    assert data["has_grassroots"] is None


def test_update_me_exclude_unset_preserves_existing(client, auth_headers):
    """PUT /api/auth/me 只传部分字段 → 未传的身份字段保持原值（exclude_unset 语义）。"""
    # 先保存完整身份
    client.put(
        "/api/auth/me",
        json={
            "fresh_status": "应届",
            "party_status": "中共党员",
            "education": "博士",
        },
        headers=auth_headers,
    )
    # 只更新 party_status
    resp = client.put(
        "/api/auth/me",
        json={"party_status": "群众"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fresh_status"] == "应届"  # 保持原值
    assert data["party_status"] == "群众"  # 更新
    assert data["education"] == "博士"  # 保持原值
