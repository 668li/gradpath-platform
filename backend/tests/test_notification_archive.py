# tests/test_notification_archive.py
"""C4 通知归档 API 集成测试。

覆盖场景：
- 归档单条通知（POST /{id}/archive）
- 恢复归档通知（POST /{id}/unarchive）
- 批量归档（POST /archive 带 notification_ids）
- 批量归档全部已读（POST /archive 不带 ids + only_read=true）
- 自动归档旧通知（POST /archive-old?days_old=30）
- 列表 ?archived=false 默认行为（归档通知不出现在主列表）
- unread_count 只统计未归档未读
- mark_all_as_read 只影响未归档通知
- 归档不存在的通知返回 404 NotFoundError
- 批量超过 200 条返回 BusinessError
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.models.notification import Notification, NotificationType
from app.models.user import User


class TestNotificationArchive:
    """C4 通知归档 API 测试套件。"""

    def _get_user_id(self, db_session) -> str:
        user = db_session.query(User).first()
        return str(user.id)

    def _create_notification(
        self,
        db_session,
        user_id,
        type="system",
        title="Test",
        content="Body",
        read=False,
        archived=False,
        days_ago: int = 0,
    ) -> Notification:
        """创建测试通知。

        Args:
            days_ago: created_at/updated_at 偏移天数（用于测试自动归档阈值）
        """
        n = Notification(
            user_id=user_id,
            type=NotificationType(type),
            title=title,
            content=content,
            read=read,
            archived=archived,
        )
        if days_ago > 0:
            past = datetime.now(timezone.utc) - timedelta(days=days_ago)
            n.created_at = past
            n.updated_at = past
        db_session.add(n)
        db_session.commit()
        db_session.refresh(n)
        return n

    # ===== 单条归档/恢复 =====

    def test_archive_single_success(self, client: TestClient, auth_headers: dict, db_session):
        """归档单条通知成功。"""
        uid = self._get_user_id(db_session)
        n = self._create_notification(db_session, uid, title="待归档")

        resp = client.post(f"/api/notifications/{n.id}/archive", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(n.id)
        assert body["archived"] is True
        assert body["archived_at"] is not None

    def test_archive_single_idempotent(self, client: TestClient, auth_headers: dict, db_session):
        """重复归档同一条通知应幂等返回 200。"""
        uid = self._get_user_id(db_session)
        n = self._create_notification(db_session, uid, title="幂等归档")

        r1 = client.post(f"/api/notifications/{n.id}/archive", headers=auth_headers)
        assert r1.status_code == 200
        first_archived_at = r1.json()["archived_at"]

        r2 = client.post(f"/api/notifications/{n.id}/archive", headers=auth_headers)
        assert r2.status_code == 200
        assert r2.json()["archived"] is True
        # 幂等：archived_at 不变
        assert r2.json()["archived_at"] == first_archived_at

    def test_archive_single_not_found(self, client: TestClient, auth_headers: dict):
        """归档不存在的通知返回 404。"""
        resp = client.post(
            f"/api/notifications/{uuid4()}/archive",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        body = resp.json()
        assert body.get("code") == "NOT_FOUND"

    def test_unarchive_single_success(self, client: TestClient, auth_headers: dict, db_session):
        """恢复归档通知成功，archived_at 清空。"""
        uid = self._get_user_id(db_session)
        n = self._create_notification(db_session, uid, title="恢复归档", archived=True)
        n.archived_at = datetime.now(timezone.utc)
        db_session.commit()

        resp = client.post(f"/api/notifications/{n.id}/unarchive", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["archived"] is False
        assert body["archived_at"] is None

    def test_unarchive_single_idempotent(self, client: TestClient, auth_headers: dict, db_session):
        """对未归档通知调用 unarchive 应幂等返回 200。"""
        uid = self._get_user_id(db_session)
        n = self._create_notification(db_session, uid, title="未归档")

        resp = client.post(f"/api/notifications/{n.id}/unarchive", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["archived"] is False
        assert resp.json()["archived_at"] is None

    def test_unarchive_single_not_found(self, client: TestClient, auth_headers: dict):
        """恢复不存在的通知返回 404。"""
        resp = client.post(
            f"/api/notifications/{uuid4()}/unarchive",
            headers=auth_headers,
        )
        assert resp.status_code == 404

    # ===== 批量归档 =====

    def test_archive_batch_by_ids(self, client: TestClient, auth_headers: dict, db_session):
        """通过 notification_ids 批量归档指定通知。"""
        uid = self._get_user_id(db_session)
        n1 = self._create_notification(db_session, uid, title="B1")
        n2 = self._create_notification(db_session, uid, title="B2")
        # 这条不应被归档
        n3 = self._create_notification(db_session, uid, title="B3-保留")

        resp = client.post(
            "/api/notifications/archive",
            headers=auth_headers,
            json={"notification_ids": [str(n1.id), str(n2.id)]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["archived_count"] == 2
        assert body["message"] == "归档完成"

        # 验证 n1/n2 已归档，n3 仍在主列表
        list_resp = client.get("/api/notifications", headers=auth_headers)
        assert list_resp.status_code == 200
        titles = [it["title"] for it in list_resp.json()["items"]]
        assert "B3-保留" in titles
        assert "B1" not in titles
        assert "B2" not in titles

        arch_resp = client.get("/api/notifications?archived=true", headers=auth_headers)
        arch_titles = [it["title"] for it in arch_resp.json()["items"]]
        assert "B1" in arch_titles
        assert "B2" in arch_titles

    def test_archive_batch_all_read(self, client: TestClient, auth_headers: dict, db_session):
        """不带 ids + only_read=true 归档所有已读通知。"""
        uid = self._get_user_id(db_session)
        # 2 条已读 + 1 条未读
        r1 = self._create_notification(db_session, uid, title="R1", read=True)
        r2 = self._create_notification(db_session, uid, title="R2", read=True)
        u1 = self._create_notification(db_session, uid, title="U1", read=False)

        resp = client.post(
            "/api/notifications/archive",
            headers=auth_headers,
            json={"notification_ids": None, "only_read": True},
        )
        assert resp.status_code == 200
        assert resp.json()["archived_count"] == 2

        # 主列表只剩 U1
        list_resp = client.get("/api/notifications", headers=auth_headers)
        titles = [it["title"] for it in list_resp.json()["items"]]
        assert titles == ["U1"]

    def test_archive_batch_all_unread_included(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """不带 ids + only_read=false 归档所有通知（包括未读）。"""
        uid = self._get_user_id(db_session)
        self._create_notification(db_session, uid, title="R1", read=True)
        self._create_notification(db_session, uid, title="U1", read=False)

        resp = client.post(
            "/api/notifications/archive",
            headers=auth_headers,
            json={"notification_ids": None, "only_read": False},
        )
        assert resp.status_code == 200
        assert resp.json()["archived_count"] == 2

        # 主列表为空
        list_resp = client.get("/api/notifications", headers=auth_headers)
        assert list_resp.json()["total"] == 0

    def test_archive_batch_empty_ids(self, client: TestClient, auth_headers: dict, db_session):
        """传空 notification_ids 列表应返回 0，不归档任何通知。"""
        uid = self._get_user_id(db_session)
        self._create_notification(db_session, uid, title="保留")

        resp = client.post(
            "/api/notifications/archive",
            headers=auth_headers,
            json={"notification_ids": [], "only_read": True},
        )
        assert resp.status_code == 200
        assert resp.json()["archived_count"] == 0

    def test_archive_batch_exceeds_limit(self, client: TestClient, auth_headers: dict, db_session):
        """批量归档超过 200 条限制应返回 BusinessError 400。"""
        ids = [str(uuid4()) for _ in range(201)]
        resp = client.post(
            "/api/notifications/archive",
            headers=auth_headers,
            json={"notification_ids": ids},
        )
        assert resp.status_code == 400
        body = resp.json()
        assert body.get("code") == "ARCHIVE_BATCH_TOO_LARGE"

    def test_archive_batch_invalid_ids_skipped(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """批量归档时无效 ID 应被跳过，不报错。"""
        uid = self._get_user_id(db_session)
        n1 = self._create_notification(db_session, uid, title="有效")

        resp = client.post(
            "/api/notifications/archive",
            headers=auth_headers,
            json={"notification_ids": [str(n1.id), "not-a-uuid", ""]},
        )
        assert resp.status_code == 200
        assert resp.json()["archived_count"] == 1

    # ===== 自动归档旧通知 =====

    def test_archive_old_default_threshold(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """days_old=30 默认阈值，超过 30 天的已读通知自动归档。"""
        uid = self._get_user_id(db_session)
        # 31 天前的已读通知（应被归档）
        self._create_notification(db_session, uid, title="旧已读", read=True, days_ago=31)
        # 10 天前的已读通知（保留）
        self._create_notification(db_session, uid, title="新已读", read=True, days_ago=10)
        # 31 天前的未读通知（保留 — 自动归档仅针对已读）
        self._create_notification(db_session, uid, title="旧未读", read=False, days_ago=31)

        resp = client.post(
            "/api/notifications/archive-old?days_old=30",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["archived_count"] == 1

        # 主列表应仍有 2 条
        list_resp = client.get("/api/notifications", headers=auth_headers)
        titles = {it["title"] for it in list_resp.json()["items"]}
        assert "新已读" in titles
        assert "旧未读" in titles
        assert "旧已读" not in titles

    def test_archive_old_invalid_days_too_small(
        self, client: TestClient, auth_headers: dict
    ):
        """days_old < 1 应返回 422。"""
        resp = client.post(
            "/api/notifications/archive-old?days_old=0",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_archive_old_invalid_days_too_large(
        self, client: TestClient, auth_headers: dict
    ):
        """days_old > 365 应返回 422。"""
        resp = client.post(
            "/api/notifications/archive-old?days_old=366",
            headers=auth_headers,
        )
        assert resp.status_code == 422

    # ===== 列表与未读计数行为 =====

    def test_list_default_excludes_archived(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """默认列表 (?archived=false) 不包含归档通知。"""
        uid = self._get_user_id(db_session)
        self._create_notification(db_session, uid, title="正常")
        self._create_notification(db_session, uid, title="已归档", archived=True)

        resp = client.get("/api/notifications", headers=auth_headers)
        assert resp.status_code == 200
        titles = [it["title"] for it in resp.json()["items"]]
        assert "正常" in titles
        assert "已归档" not in titles

    def test_list_archived_true_returns_only_archived(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """?archived=true 仅返回归档通知。"""
        uid = self._get_user_id(db_session)
        self._create_notification(db_session, uid, title="正常")
        self._create_notification(db_session, uid, title="已归档", archived=True)

        resp = client.get("/api/notifications?archived=true", headers=auth_headers)
        assert resp.status_code == 200
        titles = [it["title"] for it in resp.json()["items"]]
        assert titles == ["已归档"]

    def test_unread_count_excludes_archived(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """未读计数仅统计未归档的未读通知。"""
        uid = self._get_user_id(db_session)
        # 未归档未读 — 计入
        self._create_notification(db_session, uid, title="未读", read=False)
        # 已归档未读 — 不计入
        self._create_notification(
            db_session, uid, title="归档未读", read=False, archived=True
        )

        resp = client.get("/api/notifications/unread-count", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["unread_count"] == 1

    def test_mark_all_as_read_skips_archived(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """全部标记已读不影响归档通知。"""
        uid = self._get_user_id(db_session)
        n1 = self._create_notification(db_session, uid, title="未读", read=False)
        n2 = self._create_notification(
            db_session, uid, title="归档未读", read=False, archived=True
        )

        resp = client.post("/api/notifications/read-all", headers=auth_headers)
        assert resp.status_code == 200

        # 验证 n1 已读
        db_session.refresh(n1)
        assert n1.read is True

        # 验证 n2 仍为未读
        db_session.refresh(n2)
        assert n2.read is False

    def test_list_unread_only_with_archived(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """?unread_only=true 与 ?archived=true 组合查询归档区未读通知。"""
        uid = self._get_user_id(db_session)
        # 未归档未读
        self._create_notification(db_session, uid, title="未归档未读", read=False)
        # 已归档未读
        self._create_notification(
            db_session, uid, title="归档未读", read=False, archived=True
        )
        # 已归档已读
        self._create_notification(
            db_session, uid, title="归档已读", read=True, archived=True
        )

        # 默认列表（未归档）只看到「未归档未读」
        resp1 = client.get("/api/notifications?unread_only=true", headers=auth_headers)
        titles1 = [it["title"] for it in resp1.json()["items"]]
        assert titles1 == ["未归档未读"]

        # 归档区+未读只看到「归档未读」
        resp2 = client.get(
            "/api/notifications?archived=true&unread_only=true",
            headers=auth_headers,
        )
        titles2 = [it["title"] for it in resp2.json()["items"]]
        assert titles2 == ["归档未读"]

    # ===== 跨用户隔离 =====

    def test_archive_cross_user_isolation(
        self, client: TestClient, auth_headers: dict, db_session
    ):
        """归档操作不能影响其他用户的通知。"""
        uid_a = self._get_user_id(db_session)
        # 用户 A 创建一条通知
        n_a = self._create_notification(db_session, uid_a, title="A的通知")

        # 创建用户 B 并登录
        client.post(
            "/api/auth/register",
            json={
                "email": "userb@example.com",
                "password": "Test1234!",
                "name": "用户B",
                "agree_terms": True,
            },
        )
        login_b = client.post(
            "/api/auth/login",
            json={"email": "userb@example.com", "password": "Test1234!"},
        )
        headers_b = {"Authorization": f"Bearer {login_b.json()['access_token']}"}

        # 用户 B 尝试归档用户 A 的通知 — 应返回 404
        resp = client.post(f"/api/notifications/{n_a.id}/archive", headers=headers_b)
        assert resp.status_code == 404

        # 验证用户 A 的通知仍未归档
        db_session.refresh(n_a)
        assert n_a.archived is False
