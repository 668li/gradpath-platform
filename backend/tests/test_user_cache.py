# backend/tests/test_user_cache.py
"""用户缓存测试 — 验证 get_current_user 与 build_user_context 的 Redis 缓存。

覆盖：
- get_current_user 缓存命中：第二次相同 token 不打 DB
- get_current_user 缓存未命中：首次打 DB 并写缓存
- get_current_user 无效 token 不写缓存
- Redis 不可用时降级到直接打 DB
- build_user_context 缓存命中
- build_user_context 缓存未命中写缓存
- 事件 CRUD 失效 user_context 缓存
"""
from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import event

from app.core.cache import cache
from app.models.career_event import EventType
from app.models.user import User
from app.schemas.event import EventCreate
from app.services.chat_service import build_user_context
from app.services.event_service import create_event


# ======================================================================
# 辅助函数
# ======================================================================

def _count_queries(db_session, func):
    """统计 func 执行期间发生的 SQL 查询次数。"""
    query_count = 0

    @event.listens_for(db_session.bind, "before_cursor_execute")
    def _counter(*args, **kwargs):
        nonlocal query_count
        query_count += 1

    try:
        result = func()
    finally:
        event.remove(db_session.bind, "before_cursor_execute", _counter)
    return result, query_count


# ======================================================================
# get_current_user 缓存
# ======================================================================

class TestGetCurrentUserCache:
    def test_cache_miss_hits_db_and_writes_cache(self, auth_headers, client, db_session):
        """首次请求打 DB 并写缓存。"""
        # auth_headers 已注册并登录，但未调用 get_current_user，缓存应为空
        user = db_session.query(User).filter_by(email="test@example.com").first()
        assert user is not None
        assert cache.get(f"user:{user.id}") is None

        resp = client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

        # 缓存应已写入
        cached = cache.get(f"user:{user.id}")
        assert cached is not None
        assert cached["email"] == "test@example.com"
        assert cached["name"] == "测试用户"

    def test_cache_hit_skips_db(self, auth_headers, client, db_session):
        """第二次相同 token 命中缓存，不打 DB。"""
        # 第一次请求：打 DB，写缓存
        resp1 = client.get("/api/auth/me", headers=auth_headers)
        assert resp1.status_code == 200

        # 第二次请求：应命中缓存，0 DB 查询
        # 通过临时挂载 event listener 统计查询次数
        query_count = 0

        @event.listens_for(db_session.bind, "before_cursor_execute")
        def _counter(*args, **kwargs):
            nonlocal query_count
            query_count += 1

        try:
            resp2 = client.get("/api/auth/me", headers=auth_headers)
        finally:
            event.remove(db_session.bind, "before_cursor_execute", _counter)

        assert resp2.status_code == 200
        assert resp2.json()["email"] == "test@example.com"
        # 缓存命中，无任何 DB 查询
        assert query_count == 0

    def test_invalid_token_does_not_write_cache(self, client):
        """无效 token 不写缓存（401 不应触发缓存写入）。"""
        resp = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token-string"},
        )
        assert resp.status_code == 401
        # 缓存中不应有任何 user: 开头的键
        keys = cache.keys()
        user_keys = [k for k in keys if k.startswith("user:")]
        assert user_keys == []

    def test_redis_unavailable_falls_back_to_db(self, auth_headers, client, db_session):
        """cache.get 抛异常时降级到直接打 DB，请求仍成功。"""
        # 预填充缓存
        client.get("/api/auth/me", headers=auth_headers)

        # mock cache.get 抛异常（模拟 Redis 不可用）
        with patch.object(cache, "get", side_effect=Exception("Redis down")):
            resp = client.get("/api/auth/me", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"

    def test_cache_set_failure_does_not_block_request(self, auth_headers, client, db_session):
        """cache.set 抛异常时不阻塞请求（降级到无缓存模式）。"""
        # 清空缓存确保首次请求会尝试写缓存
        cache.clear()

        with patch.object(cache, "set", side_effect=Exception("Redis write failed")):
            resp = client.get("/api/auth/me", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json()["email"] == "test@example.com"


# ======================================================================
# build_user_context 缓存
# ======================================================================

class TestBuildUserContextCache:
    def test_cache_miss_hits_db_and_writes_cache(self, db_session):
        """首次调用 build_user_context 打 DB 并写缓存。"""
        user = User(
            email="ctx@example.com",
            password_hash="hash",
            name="Ctx用户",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        assert cache.get(f"user_context:{user.id}") is None

        ctx = build_user_context(db_session, user.id)
        assert "【用户画像】" in ctx
        assert "Ctx用户" in ctx

        cached = cache.get(f"user_context:{user.id}")
        assert cached is not None
        assert cached == ctx

    def test_cache_hit_skips_db(self, db_session):
        """第二次调用 build_user_context 命中缓存，不打 DB。"""
        user = User(
            email="ctx2@example.com",
            password_hash="hash",
            name="Ctx用户2",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # 第一次调用：打 DB，写缓存
        ctx1 = build_user_context(db_session, user.id)
        assert "【用户画像】" in ctx1

        # 第二次调用：应命中缓存，0 DB 查询
        result, query_count = _count_queries(
            db_session, lambda: build_user_context(db_session, user.id)
        )

        assert result == ctx1
        assert query_count == 0

    def test_cache_hit_returns_same_string(self, db_session):
        """缓存命中返回的字符串与首次构建完全一致。"""
        user = User(
            email="ctx3@example.com",
            password_hash="hash",
            name="Ctx用户3",
            school="测试大学",
            major="测试专业",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        ctx1 = build_user_context(db_session, user.id)
        ctx2 = build_user_context(db_session, user.id)

        assert ctx1 == ctx2
        assert "测试大学" in ctx2
        assert "测试专业" in ctx2

    def test_cache_get_failure_falls_back_to_db(self, db_session):
        """cache.get 抛异常时降级到直接打 DB。"""
        user = User(
            email="ctx4@example.com",
            password_hash="hash",
            name="Ctx用户4",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # 预填充缓存
        build_user_context(db_session, user.id)

        # mock cache.get 抛异常，应降级到 DB
        with patch.object(cache, "get", side_effect=Exception("Redis down")):
            ctx = build_user_context(db_session, user.id)

        assert "【用户画像】" in ctx
        assert "Ctx用户4" in ctx


# ======================================================================
# 缓存失效
# ======================================================================

class TestCacheInvalidation:
    def test_event_create_invalidates_user_context_cache(self, db_session):
        """创建 CareerEvent 后失效 user_context 缓存。"""
        user = User(
            email="evt@example.com",
            password_hash="hash",
            name="Evt用户",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # 预填充缓存
        build_user_context(db_session, user.id)
        assert cache.get(f"user_context:{user.id}") is not None

        # 创建事件
        create_event(
            db_session,
            user.id,
            EventCreate(
                event_date=date.today(),
                event_type=EventType.other,
                title="新事件",
            ),
        )

        # 缓存应已失效
        assert cache.get(f"user_context:{user.id}") is None

    def test_event_update_invalidates_user_context_cache(self, db_session):
        """更新 CareerEvent 后失效 user_context 缓存。"""
        from app.services.event_service import update_event
        from app.schemas.event import EventUpdate

        user = User(
            email="evt2@example.com",
            password_hash="hash",
            name="Evt用户2",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        evt = create_event(
            db_session,
            user.id,
            EventCreate(
                event_date=date.today(),
                event_type=EventType.other,
                title="原标题",
            ),
        )

        # 预填充缓存
        build_user_context(db_session, user.id)
        assert cache.get(f"user_context:{user.id}") is not None

        # 更新事件
        update_event(
            db_session,
            user.id,
            evt.id,
            EventUpdate(title="新标题"),
        )

        assert cache.get(f"user_context:{user.id}") is None

    def test_event_delete_invalidates_user_context_cache(self, db_session):
        """删除 CareerEvent 后失效 user_context 缓存。"""
        from app.services.event_service import delete_event

        user = User(
            email="evt3@example.com",
            password_hash="hash",
            name="Evt用户3",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        evt = create_event(
            db_session,
            user.id,
            EventCreate(
                event_date=date.today(),
                event_type=EventType.other,
                title="待删除事件",
            ),
        )

        # 预填充缓存
        build_user_context(db_session, user.id)
        assert cache.get(f"user_context:{user.id}") is not None

        delete_event(db_session, user.id, evt.id)

        assert cache.get(f"user_context:{user.id}") is None

    def test_change_password_invalidates_user_cache(self, auth_headers, client, db_session):
        """修改密码后失效 user 缓存。"""
        from app.models.user import User

        # 预填充 user 缓存
        client.get("/api/auth/me", headers=auth_headers)
        user = db_session.query(User).filter_by(email="test@example.com").first()
        assert cache.get(f"user:{user.id}") is not None

        # 修改密码
        resp = client.post(
            "/api/auth/change-password",
            json={"current_password": "Test1234!", "new_password": "NewPass1!"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # user 缓存应已失效
        assert cache.get(f"user:{user.id}") is None
