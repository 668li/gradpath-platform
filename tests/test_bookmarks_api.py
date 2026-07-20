# tests/test_bookmarks_api.py
"""收藏 API 集成测试。"""
import pytest
from fastapi.testclient import TestClient


class TestBookmarkAPI:
    def test_add_bookmark(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/bookmarks",
            json={"target_type": "school", "target_id": "school-001"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["target_type"] == "school"
        assert data["target_id"] == "school-001"
        assert "id" in data
        assert "created_at" in data

    def test_add_bookmark_duplicate(self, client: TestClient, auth_headers: dict):
        client.post(
            "/api/bookmarks",
            json={"target_type": "school", "target_id": "school-001"},
            headers=auth_headers,
        )
        resp = client.post(
            "/api/bookmarks",
            json={"target_type": "school", "target_id": "school-001"},
            headers=auth_headers,
        )
        assert resp.status_code == 409

    def test_list_bookmarks(self, client: TestClient, auth_headers: dict):
        client.post(
            "/api/bookmarks",
            json={"target_type": "mentor", "target_id": "mentor-001"},
            headers=auth_headers,
        )
        client.post(
            "/api/bookmarks",
            json={"target_type": "post", "target_id": "post-001"},
            headers=auth_headers,
        )
        resp = client.get("/api/bookmarks", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2

    def test_list_bookmarks_filter_type(self, client: TestClient, auth_headers: dict):
        client.post(
            "/api/bookmarks",
            json={"target_type": "school", "target_id": "s1"},
            headers=auth_headers,
        )
        client.post(
            "/api/bookmarks",
            json={"target_type": "post", "target_id": "p1"},
            headers=auth_headers,
        )
        resp = client.get("/api/bookmarks?target_type=school", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["target_type"] == "school"

    def test_remove_bookmark(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/bookmarks",
            json={"target_type": "school", "target_id": "school-001"},
            headers=auth_headers,
        )
        bookmark_id = resp.json()["id"]
        resp = client.delete(f"/api/bookmarks/{bookmark_id}", headers=auth_headers)
        assert resp.status_code == 204
        resp = client.get("/api/bookmarks", headers=auth_headers)
        assert resp.json()["total"] == 0

    def test_remove_bookmark_not_found(self, client: TestClient, auth_headers: dict):
        resp = client.delete(
            "/api/bookmarks/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_unauthorized(self, client: TestClient):
        resp = client.get("/api/bookmarks")
        assert resp.status_code in (401, 403)
