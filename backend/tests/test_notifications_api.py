# tests/test_notifications_api.py
"""通知 API 集成测试。"""
import pytest
from fastapi.testclient import TestClient

from app.models.notification import Notification, NotificationType
from app.models.user import User


class TestNotificationAPI:
    def _create_notification(self, db_session, user_id, type="system", title="Test", content="Body", read=False):
        n = Notification(
            user_id=user_id,
            type=NotificationType(type),
            title=title,
            content=content,
            read=read,
        )
        db_session.add(n)
        db_session.commit()
        db_session.refresh(n)
        return n

    def _get_user_id(self, db_session) -> str:
        user = db_session.query(User).first()
        return str(user.id)

    def test_list_empty(self, client: TestClient, auth_headers: dict):
        resp = client.get("/api/notifications", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["unread_count"] == 0
        assert data["items"] == []

    def test_unread_count(self, client: TestClient, auth_headers: dict, db_session):
        uid = self._get_user_id(db_session)
        self._create_notification(db_session, uid, title="N1")
        self._create_notification(db_session, uid, title="N2", read=True)
        resp = client.get("/api/notifications/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 1

    def test_mark_as_read(self, client: TestClient, auth_headers: dict, db_session):
        uid = self._get_user_id(db_session)
        n = self._create_notification(db_session, uid, title="Unread")
        resp = client.put(f"/api/notifications/{n.id}/read", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["read"] is True

    def test_mark_as_read_not_found(self, client: TestClient, auth_headers: dict):
        resp = client.put(
            "/api/notifications/00000000-0000-0000-0000-000000000000/read",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_mark_all_as_read(self, client: TestClient, auth_headers: dict, db_session):
        uid = self._get_user_id(db_session)
        self._create_notification(db_session, uid, title="A")
        self._create_notification(db_session, uid, title="B")
        resp = client.post("/api/notifications/read-all", headers=auth_headers)
        assert resp.status_code == 200
        resp = client.get("/api/notifications/unread-count", headers=auth_headers)
        assert resp.json()["unread_count"] == 0

    def test_list_with_pagination(self, client: TestClient, auth_headers: dict, db_session):
        uid = self._get_user_id(db_session)
        for i in range(25):
            self._create_notification(db_session, uid, title=f"N{i}")
        resp = client.get("/api/notifications?page=1&page_size=10", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 25
        assert len(data["items"]) == 10
        assert data["unread_count"] == 25

    def test_list_unread_only(self, client: TestClient, auth_headers: dict, db_session):
        uid = self._get_user_id(db_session)
        self._create_notification(db_session, uid, title="U1")
        self._create_notification(db_session, uid, title="R1", read=True)
        resp = client.get("/api/notifications?unread_only=true", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "U1"

    def test_unauthorized(self, client: TestClient):
        resp = client.get("/api/notifications")
        assert resp.status_code in (401, 403)
