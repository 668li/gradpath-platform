# backend/tests/test_batch_endpoints.py
"""C7 批量端点测试 — 覆盖 6 个 batch 端点。

测试范围：
1. POST   /api/posts/batch          批量获取帖子（公开，无登录，无用户隔离）
2. POST   /api/events/batch          批量获取职业事件（登录 + 用户隔离）
3. POST   /api/decisions/batch       批量获取决策（登录 + 用户隔离）
4. POST   /api/skills/batch          批量获取技能（登录 + 用户隔离）
5. POST   /api/mentors/batch         批量获取导师（公开，无登录，无用户隔离）
6. DELETE /api/notifications/batch   批量删除通知（登录 + 用户隔离）

每个端点通用校验维度：
- max_length=100 上限校验
- 无效 UUID 被跳过（不报 500，不返回错误 ID）
- 空列表 min_length=1 校验（DELETE 除外，DELETE 无 min_length）
- 跨用户隔离（仅返回/删除当前用户资源，越权 ID 被静默忽略）
- 未登录访问需鉴权端点返回 401
- 不存在的 ID 不在结果中
"""
from datetime import date
from uuid import uuid4

import pytest

from app.models.career_event import CareerEvent, EventType
from app.models.destination_decision import (
    DecisionStatus,
    DestinationDecision,
    DestinationType,
)
from app.models.mentor import Mentor
from app.models.notification import Notification, NotificationType
from app.models.post import Post, PostTopicType
from app.models.skill_node import SkillNode
from app.models.user import User


# ======================================================================
# 辅助：注册第二个用户，用于跨用户隔离测试
# ======================================================================

def _register_second_user(client, email="other@example.com",
                          password="Other1234!", name="其他用户"):
    """注册第二个用户，返回 (token, user_id)。"""
    client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_current_user_id(db_session) -> str:
    """获取 auth_headers fixture 创建的测试用户 ID。"""
    user = db_session.query(User).filter(User.email == "test@example.com").first()
    return str(user.id)


# ======================================================================
# 1. POST /api/posts/batch — 批量获取帖子（公开）
# ======================================================================

class TestPostsBatch:
    """帖子批量获取端点测试。

    公开端点（无需登录），不按 user_id 过滤（社区帖子对所有用户可见）。
    """

    def _create_post(self, client, headers, content="测试帖子"):
        resp = client.post(
            "/api/posts",
            headers=headers,
            json={
                "topic_type": "school_major",
                "topic_key": "清华|计算机",
                "content": content,
            },
        )
        assert resp.status_code == 201
        return resp.json()

    def test_batch_returns_matching_posts(self, auth_headers, client):
        """传入多个有效 ID 应返回对应帖子。"""
        p1 = self._create_post(client, auth_headers, content="帖子-1")
        p2 = self._create_post(client, auth_headers, content="帖子-2")
        p3 = self._create_post(client, auth_headers, content="帖子-3")

        resp = client.post(
            "/api/posts/batch",
            json={"ids": [p1["id"], p2["id"], p3["id"]]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3
        ids = {it["id"] for it in items}
        assert ids == {p1["id"], p2["id"], p3["id"]}
        # 校验响应字段完整
        for it in items:
            assert "author_id" in it
            assert "author_name" in it
            assert "content" in it
            assert "topic_type" in it

    def test_batch_invalid_uuid_skipped(self, auth_headers, client):
        """无效 UUID 应被跳过，不导致 500。"""
        p1 = self._create_post(client, auth_headers, content="有效帖")
        resp = client.post(
            "/api/posts/batch",
            json={"ids": [p1["id"], "not-a-uuid", "also-invalid"]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == p1["id"]

    def test_batch_all_invalid_uuid_returns_empty(self, client):
        """全部为无效 UUID 时返回空列表。"""
        resp = client.post(
            "/api/posts/batch",
            json={"ids": ["not-a-uuid", "also-invalid", "!!!"]},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_batch_nonexistent_ids_returns_empty(self, client):
        """传入不存在的 UUID 应返回空列表。"""
        resp = client.post(
            "/api/posts/batch",
            json={"ids": [str(uuid4()), str(uuid4())]},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_batch_empty_ids_returns_422(self, client):
        """空 ID 列表应触发 min_length=1 校验返回 422。"""
        resp = client.post("/api/posts/batch", json={"ids": []})
        assert resp.status_code == 422

    def test_batch_too_many_ids_returns_422(self, auth_headers, client):
        """超过 100 个 ID 应触发 max_length=100 校验返回 422。"""
        ids = [str(uuid4()) for _ in range(101)]
        resp = client.post("/api/posts/batch", json={"ids": ids})
        assert resp.status_code == 422

    def test_batch_no_auth_required(self, auth_headers, client):
        """批量获取帖子无需登录。"""
        p1 = self._create_post(client, auth_headers, content="无登录测试")
        # 不带 Authorization 头调用
        resp = client.post("/api/posts/batch", json={"ids": [p1["id"]]})
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_batch_dedup_not_required(self, auth_headers, client):
        """重复传入同一 ID 行为定义明确（不去重也可，但不应报错）。"""
        p1 = self._create_post(client, auth_headers, content="重复 ID 测试")
        resp = client.post(
            "/api/posts/batch",
            json={"ids": [p1["id"], p1["id"]]},
        )
        assert resp.status_code == 200
        # SQL IN 查询不会重复返回，因此结果为 1
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == p1["id"]


# ======================================================================
# 2. POST /api/events/batch — 批量获取职业事件（登录 + 用户隔离）
# ======================================================================

class TestEventsBatch:
    """职业事件批量获取端点测试。

    需登录，仅返回当前用户的事件（防止越权）。
    """

    def _create_event(self, client, headers, title="测试事件"):
        resp = client.post(
            "/api/events",
            headers=headers,
            json={
                "event_date": "2026-06-01",
                "event_type": "onboard",
                "title": title,
                "description": "...",
            },
        )
        assert resp.status_code == 201
        return resp.json()

    def test_batch_returns_user_events(self, auth_headers, client):
        """传入当前用户的事件 ID 应返回对应事件。"""
        e1 = self._create_event(client, auth_headers, title="事件-1")
        e2 = self._create_event(client, auth_headers, title="事件-2")

        resp = client.post(
            "/api/events/batch",
            headers=auth_headers,
            json={"ids": [e1["id"], e2["id"]]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        ids = {it["id"] for it in items}
        assert ids == {e1["id"], e2["id"]}

    def test_batch_excludes_other_users(self, auth_headers, client):
        """跨用户隔离：传入他人事件 ID 不应返回。"""
        # 当前用户的事件
        my_event = self._create_event(client, auth_headers, title="我的事件")
        # 第二个用户的事件
        other_headers = _register_second_user(client)
        other_event = self._create_event(client, other_headers, title="他人事件")

        resp = client.post(
            "/api/events/batch",
            headers=auth_headers,
            json={"ids": [my_event["id"], other_event["id"]]},
        )
        assert resp.status_code == 200
        items = resp.json()
        # 仅返回当前用户的事件
        assert len(items) == 1
        assert items[0]["id"] == my_event["id"]
        assert items[0]["title"] == "我的事件"

    def test_batch_invalid_uuid_skipped(self, auth_headers, client):
        """无效 UUID 应被跳过。"""
        e1 = self._create_event(client, auth_headers)
        resp = client.post(
            "/api/events/batch",
            headers=auth_headers,
            json={"ids": [e1["id"], "invalid-uuid"]},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_batch_empty_ids_returns_422(self, auth_headers, client):
        """空 ID 列表返回 422。"""
        resp = client.post(
            "/api/events/batch",
            headers=auth_headers,
            json={"ids": []},
        )
        assert resp.status_code == 422

    def test_batch_too_many_ids_returns_422(self, auth_headers, client):
        """超过 100 个 ID 返回 422。"""
        ids = [str(uuid4()) for _ in range(101)]
        resp = client.post(
            "/api/events/batch",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 422

    def test_batch_no_auth_returns_401(self, client):
        """未登录访问返回 401。"""
        resp = client.post(
            "/api/events/batch",
            json={"ids": [str(uuid4())]},
        )
        assert resp.status_code == 401

    def test_batch_all_invalid_uuid_returns_empty(self, auth_headers, client):
        """全部为无效 UUID 返回空列表。"""
        resp = client.post(
            "/api/events/batch",
            headers=auth_headers,
            json={"ids": ["invalid-1", "invalid-2"]},
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ======================================================================
# 3. POST /api/decisions/batch — 批量获取决策（登录 + 用户隔离）
# ======================================================================

class TestDecisionsBatch:
    """决策批量获取端点测试。

    需登录，仅返回当前用户的决策（防止越权）。
    """

    def _create_decision(self, client, headers, reasoning="测试决策"):
        resp = client.post(
            "/api/decisions",
            headers=headers,
            json={
                "decision_date": "2026-06-27",
                "destination_type": "employment",
                "status": "planned",
                "details": {"company": "腾讯"},
                "reasoning": reasoning,
                "confidence": 4,
            },
        )
        assert resp.status_code == 201
        return resp.json()

    def test_batch_returns_user_decisions(self, auth_headers, client):
        d1 = self._create_decision(client, auth_headers, reasoning="决策-1")
        d2 = self._create_decision(client, auth_headers, reasoning="决策-2")

        resp = client.post(
            "/api/decisions/batch",
            headers=auth_headers,
            json={"ids": [d1["id"], d2["id"]]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        ids = {it["id"] for it in items}
        assert ids == {d1["id"], d2["id"]}

    def test_batch_excludes_other_users(self, auth_headers, client):
        """跨用户隔离：传入他人决策 ID 不应返回。"""
        my_decision = self._create_decision(client, auth_headers, reasoning="我的决策")
        other_headers = _register_second_user(client)
        other_decision = self._create_decision(client, other_headers, reasoning="他人决策")

        resp = client.post(
            "/api/decisions/batch",
            headers=auth_headers,
            json={"ids": [my_decision["id"], other_decision["id"]]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["id"] == my_decision["id"]
        assert items[0]["reasoning"] == "我的决策"

    def test_batch_invalid_uuid_skipped(self, auth_headers, client):
        d1 = self._create_decision(client, auth_headers)
        resp = client.post(
            "/api/decisions/batch",
            headers=auth_headers,
            json={"ids": [d1["id"], "invalid"]},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_batch_empty_ids_returns_422(self, auth_headers, client):
        resp = client.post(
            "/api/decisions/batch",
            headers=auth_headers,
            json={"ids": []},
        )
        assert resp.status_code == 422

    def test_batch_too_many_ids_returns_422(self, auth_headers, client):
        ids = [str(uuid4()) for _ in range(101)]
        resp = client.post(
            "/api/decisions/batch",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 422

    def test_batch_no_auth_returns_401(self, client):
        resp = client.post(
            "/api/decisions/batch",
            json={"ids": [str(uuid4())]},
        )
        assert resp.status_code == 401


# ======================================================================
# 4. POST /api/skills/batch — 批量获取技能（登录 + 用户隔离）
# ======================================================================

class TestSkillsBatch:
    """技能批量获取端点测试。

    需登录，仅返回当前用户的技能（防止越权）。
    """

    def _create_skill(self, client, headers, name="Python"):
        resp = client.post(
            "/api/skills",
            headers=headers,
            json={
                "name": name,
                "category": "后端",
                "level": 4,
            },
        )
        assert resp.status_code == 201
        return resp.json()

    def test_batch_returns_user_skills(self, auth_headers, client):
        s1 = self._create_skill(client, auth_headers, name="Python")
        s2 = self._create_skill(client, auth_headers, name="Go")

        resp = client.post(
            "/api/skills/batch",
            headers=auth_headers,
            json={"ids": [s1["id"], s2["id"]]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 2
        names = {it["name"] for it in items}
        assert names == {"Python", "Go"}

    def test_batch_excludes_other_users(self, auth_headers, client):
        """跨用户隔离。"""
        my_skill = self._create_skill(client, auth_headers, name="我的技能")
        other_headers = _register_second_user(client)
        other_skill = self._create_skill(client, other_headers, name="他人技能")

        resp = client.post(
            "/api/skills/batch",
            headers=auth_headers,
            json={"ids": [my_skill["id"], other_skill["id"]]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 1
        assert items[0]["name"] == "我的技能"

    def test_batch_invalid_uuid_skipped(self, auth_headers, client):
        s1 = self._create_skill(client, auth_headers)
        resp = client.post(
            "/api/skills/batch",
            headers=auth_headers,
            json={"ids": [s1["id"], "invalid"]},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_batch_empty_ids_returns_422(self, auth_headers, client):
        resp = client.post(
            "/api/skills/batch",
            headers=auth_headers,
            json={"ids": []},
        )
        assert resp.status_code == 422

    def test_batch_too_many_ids_returns_422(self, auth_headers, client):
        ids = [str(uuid4()) for _ in range(101)]
        resp = client.post(
            "/api/skills/batch",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 422

    def test_batch_no_auth_returns_401(self, client):
        resp = client.post(
            "/api/skills/batch",
            json={"ids": [str(uuid4())]},
        )
        assert resp.status_code == 401


# ======================================================================
# 5. POST /api/mentors/batch — 批量获取导师（公开）
# ======================================================================

class TestMentorsBatch:
    """导师批量获取端点测试。

    公开端点（无需登录），导师数据对所有用户可见。
    """

    def _seed_mentors(self, db_session, count=3):
        mentors = []
        for i in range(count):
            m = Mentor(
                name=f"导师-{i}",
                university="清华大学",
                department="计算机系",
                title="教授",
                avg_rating=4.0 + i * 0.1,
            )
            db_session.add(m)
            mentors.append(m)
        db_session.commit()
        return mentors

    def test_batch_returns_matching_mentors(self, client, db_session):
        m1, m2, m3 = self._seed_mentors(db_session, 3)

        resp = client.post(
            "/api/mentors/batch",
            json={"ids": [str(m1.id), str(m2.id), str(m3.id)]},
        )
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) == 3
        ids = {it["id"] for it in items}
        assert ids == {str(m1.id), str(m2.id), str(m3.id)}
        # 校验响应字段
        for it in items:
            assert "name" in it
            assert "university" in it
            assert "avg_rating" in it

    def test_batch_invalid_uuid_skipped(self, client, db_session):
        m1, *_ = self._seed_mentors(db_session, 1)
        resp = client.post(
            "/api/mentors/batch",
            json={"ids": [str(m1.id), "not-a-uuid"]},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_batch_all_invalid_uuid_returns_empty(self, client):
        resp = client.post(
            "/api/mentors/batch",
            json={"ids": ["invalid-1", "invalid-2"]},
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_batch_empty_ids_returns_422(self, client):
        resp = client.post("/api/mentors/batch", json={"ids": []})
        assert resp.status_code == 422

    def test_batch_too_many_ids_returns_422(self, client):
        ids = [str(uuid4()) for _ in range(101)]
        resp = client.post("/api/mentors/batch", json={"ids": ids})
        assert resp.status_code == 422

    def test_batch_no_auth_required(self, client, db_session):
        """批量获取导师无需登录。"""
        m1, *_ = self._seed_mentors(db_session, 1)
        resp = client.post(
            "/api/mentors/batch",
            json={"ids": [str(m1.id)]},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_batch_nonexistent_ids_returns_empty(self, client):
        """不存在的 UUID 返回空列表。"""
        resp = client.post(
            "/api/mentors/batch",
            json={"ids": [str(uuid4()), str(uuid4())]},
        )
        assert resp.status_code == 200
        assert resp.json() == []


# ======================================================================
# 6. DELETE /api/notifications/batch — 批量删除通知（登录 + 用户隔离）
# ======================================================================

class TestNotificationsBatchDelete:
    """通知批量删除端点测试。

    需登录，仅删除当前用户的通知（防止越权删除他人通知）。
    返回 {"deleted": int}。
    """

    def _create_notification(self, db_session, user_id, title="测试通知"):
        n = Notification(
            user_id=user_id,
            type=NotificationType.system,
            title=title,
            content="内容",
        )
        db_session.add(n)
        db_session.commit()
        db_session.refresh(n)
        return n

    def test_batch_delete_returns_count(self, auth_headers, client, db_session):
        """批量删除应返回删除条数。"""
        uid = _get_current_user_id(db_session)
        n1 = self._create_notification(db_session, uid, title="N1")
        n2 = self._create_notification(db_session, uid, title="N2")

        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            headers=auth_headers,
            json={"ids": [str(n1.id), str(n2.id)]},
        )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": 2}

    def test_batch_delete_excludes_other_users(self, auth_headers, client, db_session):
        """跨用户隔离：不应删除他人的通知。"""
        # 当前用户的通知
        my_uid = _get_current_user_id(db_session)
        my_n = self._create_notification(db_session, my_uid, title="我的通知")

        # 第二个用户的通知
        other_headers = _register_second_user(client)
        # 通过 /api/auth/me 等价方式拿 ID — 直接查 DB
        other_user = db_session.query(User).filter(
            User.email == "other@example.com"
        ).first()
        other_n = self._create_notification(
            db_session, str(other_user.id), title="他人通知"
        )

        # 当前用户尝试删除自己 + 他人的通知
        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            headers=auth_headers,
            json={"ids": [str(my_n.id), str(other_n.id)]},
        )
        assert resp.status_code == 200
        # 只删除了 1 条（自己的）
        assert resp.json() == {"deleted": 1}

        # 验证他人的通知仍在 DB 中
        still_exists = (
            db_session.query(Notification)
            .filter(Notification.id == str(other_n.id))
            .first()
        )
        assert still_exists is not None

    def test_batch_delete_invalid_uuid_skipped(self, auth_headers, client, db_session):
        """无效 UUID 被跳过。"""
        uid = _get_current_user_id(db_session)
        n1 = self._create_notification(db_session, uid)

        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            headers=auth_headers,
            json={"ids": [str(n1.id), "not-a-uuid"]},
        )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": 1}

    def test_batch_delete_all_invalid_uuid_returns_zero(
        self, auth_headers, client
    ):
        """全部无效 UUID 返回 deleted=0。"""
        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            headers=auth_headers,
            json={"ids": ["invalid-1", "invalid-2"]},
        )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": 0}

    def test_batch_delete_nonexistent_returns_zero(self, auth_headers, client):
        """不存在的 UUID 返回 deleted=0。"""
        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            headers=auth_headers,
            json={"ids": [str(uuid4()), str(uuid4())]},
        )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": 0}

    def test_batch_delete_too_many_ids_returns_422(self, auth_headers, client):
        """超过 100 个 ID 返回 422。"""
        ids = [str(uuid4()) for _ in range(101)]
        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            headers=auth_headers,
            json={"ids": ids},
        )
        assert resp.status_code == 422

    def test_batch_delete_no_auth_returns_401(self, client):
        """未登录返回 401。"""
        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            json={"ids": [str(uuid4())]},
        )
        assert resp.status_code == 401

    def test_batch_delete_actually_deletes(self, auth_headers, client, db_session):
        """删除后通知应不再出现在列表中。"""
        uid = _get_current_user_id(db_session)
        n1 = self._create_notification(db_session, uid, title="待删除")
        n2 = self._create_notification(db_session, uid, title="保留")

        # 删除 n1
        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            headers=auth_headers,
            json={"ids": [str(n1.id)]},
        )
        assert resp.status_code == 200
        assert resp.json() == {"deleted": 1}

        # 列表中应只剩 n2
        list_resp = client.get("/api/notifications", headers=auth_headers)
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        assert len(items) == 1
        assert items[0]["title"] == "保留"


# ======================================================================
# 跨端点对比：所有需鉴权端点未登录时返回 401
# ======================================================================

class TestAuthEnforcement:
    """鉴权一致性：所有需登录的 batch 端点未登录时返回 401。"""

    def test_events_batch_requires_auth(self, client):
        resp = client.post("/api/events/batch", json={"ids": [str(uuid4())]})
        assert resp.status_code == 401

    def test_decisions_batch_requires_auth(self, client):
        resp = client.post("/api/decisions/batch", json={"ids": [str(uuid4())]})
        assert resp.status_code == 401

    def test_skills_batch_requires_auth(self, client):
        resp = client.post("/api/skills/batch", json={"ids": [str(uuid4())]})
        assert resp.status_code == 401

    def test_notifications_batch_delete_requires_auth(self, client):
        resp = client.request(
            "DELETE",
            "/api/notifications/batch",
            json={"ids": [str(uuid4())]},
        )
        assert resp.status_code == 401
