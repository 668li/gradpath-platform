# backend/tests/test_api_sources.py
"""DataSource API 测试。"""
import pytest
from app.models.user import User


@pytest.fixture
def admin_headers(client, db_session):
    from app.core.security import hash_password
    admin = User(
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestDataSourceCRUD:
    def test_create_source(self, client, admin_headers):
        resp = client.post(
            "/api/pipeline/sources",
            json={
                "name": "测试数据源",
                "source_type": "api",
                "api_url": "https://api.example.com/data",
                "api_key": "test-key",
                "is_active": True,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "测试数据源"
        assert data["is_active"] is True
        assert data["id"] is not None

    def test_list_sources(self, client, admin_headers):
        # 先创建一个
        client.post(
            "/api/pipeline/sources",
            json={"name": "数据源1", "source_type": "api"},
            headers=admin_headers,
        )
        resp = client.get("/api/pipeline/sources", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_update_source(self, client, admin_headers):
        create_resp = client.post(
            "/api/pipeline/sources",
            json={"name": "原名", "source_type": "api"},
            headers=admin_headers,
        )
        source_id = create_resp.json()["id"]
        resp = client.put(
            f"/api/pipeline/sources/{source_id}",
            json={"name": "新名", "is_active": False},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "新名"
        assert resp.json()["is_active"] is False

    def test_delete_source(self, client, admin_headers):
        create_resp = client.post(
            "/api/pipeline/sources",
            json={"name": "待删除", "source_type": "api"},
            headers=admin_headers,
        )
        source_id = create_resp.json()["id"]
        resp = client.delete(f"/api/pipeline/sources/{source_id}", headers=admin_headers)
        assert resp.status_code == 204

    def test_non_admin_blocked(self, client, db_session):
        client.post(
            "/api/auth/register",
            json={"email": "normal2@test.com", "password": "Test1234!", "name": "普通"},
        )
        resp = client.post(
            "/api/auth/login",
            json={"email": "normal2@test.com", "password": "Test1234!"},
        )
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = client.get("/api/pipeline/sources", headers=headers)
        assert resp.status_code == 403
