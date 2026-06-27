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
