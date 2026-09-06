def test_register_success(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "new@example.com", "password": "Pass1234!", "name": "新用户"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "new@example.com"
    assert data["name"] == "新用户"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email(client):
    client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "Pass1234!", "name": "用户1"},
    )
    resp = client.post(
        "/api/auth/register",
        json={"email": "dup@example.com", "password": "Pass1234!", "name": "用户2"},
    )
    assert resp.status_code == 409


def test_register_rejects_disagree_terms(client):
    """B3 合规：未同意条款时拒绝注册。"""
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "disagree@example.com",
            "password": "Pass1234!",
            "name": "用户",
            "agree_terms": False,
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "TERMS_NOT_AGREED"


def test_register_accepts_explicit_agree_terms(client):
    """B3 合规：显式 agree_terms=true 可正常注册。"""
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "agree@example.com",
            "password": "Pass1234!",
            "name": "同意用户",
            "agree_terms": True,
        },
    )
    assert resp.status_code == 201


def test_login_success(client):
    client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "Pass1234!", "name": "登录用户"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "Pass1234!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"email": "wrong@example.com", "password": "Pass1234!", "name": "用户"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "WrongPass!"},
    )
    assert resp.status_code == 401


def test_get_me(auth_headers, client):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


def test_get_me_unauthorized(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_update_me_fields(client, auth_headers):
    """轻量设置（C2）：更新昵称/学校/专业/毕业年份/简介并回读。"""
    resp = client.put(
        "/api/auth/me",
        headers=auth_headers,
        json={
            "nickname": "考研小张",
            "school": "示例大学",
            "major": "计算机科学与技术",
            "graduation_year": 2028,
            "bio": "目标是上岸。",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nickname"] == "考研小张"
    assert body["school"] == "示例大学"
    assert body["major"] == "计算机科学与技术"
    assert body["graduation_year"] == 2028
    assert body["bio"] == "目标是上岸。"
    # /me 回读一致（60s 用户缓存已主动失效，否则旧值滞留）
    me = client.get("/api/auth/me", headers=auth_headers)
    assert me.json()["nickname"] == "考研小张"


def test_update_me_clears_field_with_null(client, auth_headers):
    """None 表示清除该字段；未传字段保持不变。"""
    client.put(
        "/api/auth/me",
        headers=auth_headers,
        json={"nickname": "临时昵称", "school": "某校"},
    )
    resp = client.put(
        "/api/auth/me",
        headers=auth_headers,
        json={"nickname": None},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["nickname"] is None
    assert body["school"] == "某校", "未传字段应保持原值"


def test_update_me_rejects_invalid_graduation_year(client, auth_headers):
    resp = client.put(
        "/api/auth/me",
        headers=auth_headers,
        json={"graduation_year": 1900},
    )
    assert resp.status_code == 422


def test_update_me_unauthorized(client):
    resp = client.put("/api/auth/me", json={"nickname": "x"})
    assert resp.status_code == 401


def test_refresh_token_success(client):
    """使用有效的 refresh_token 换取新的 access_token。"""
    client.post(
        "/api/auth/register",
        json={"email": "refresh@example.com", "password": "Pass1234!", "name": "刷新用户"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "refresh@example.com", "password": "Pass1234!"},
    )
    refresh_token = resp.json()["refresh_token"]
    refresh_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200
    data = refresh_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    # 新 access_token 应可正常访问 /me
    me_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "refresh@example.com"


def test_refresh_token_invalid(client):
    """使用无效的 refresh_token 应返回 401。"""
    resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid-token-string"},
    )
    assert resp.status_code == 401


def test_refresh_token_expired(client):
    """使用已过期的 refresh_token 应返回 401。"""
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    import jwt

    from app.config import settings

    expire = datetime.now(timezone.utc) - timedelta(minutes=1)
    payload = {"sub": str(uuid4()), "exp": expire, "type": "refresh"}
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": expired_token},
    )
    assert resp.status_code == 401
