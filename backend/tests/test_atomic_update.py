"""C3 原子 UPDATE 测试 — 验证读-改-写模式被替换为原子 UPDATE。

测试策略：
1. 静态检查：服务源码中不再有 `<attr> += 1` 模式（被 _atomic_increment 替换）
2. 功能测试：单次调用功能正确（计数 +1）
3. 并发测试：多线程并发调用，最终计数 = 并发数（无丢失更新）
"""
import threading
from uuid import uuid4

import pytest


class TestAtomicUpdateStaticCheck:
    """静态检查：服务源码已用 _atomic_increment 替换 += 1。"""

    def test_comment_service_has_atomic_increment(self):
        """comment_service 定义了 _atomic_increment 辅助函数。"""
        import app.services.comment_service as cs
        assert hasattr(cs, "_atomic_increment")

    def test_experience_post_service_has_atomic_increment(self):
        """experience_post_service 定义了 _atomic_increment 辅助函数。"""
        import app.services.experience_post_service as eps
        assert hasattr(eps, "_atomic_increment")

    def test_qa_service_has_atomic_increment(self):
        """qa_service 定义了 _atomic_increment 辅助函数。"""
        import app.services.qa_service as qs
        assert hasattr(qs, "_atomic_increment")

    def test_mentor_service_has_atomic_increment(self):
        """mentor_service 定义了 _atomic_increment 辅助函数。"""
        import app.services.mentor_service as ms
        assert hasattr(ms, "_atomic_increment")

    def test_user_memory_service_uses_bulk_atomic_update(self):
        """user_memory_service.mark_used 使用 bulk 原子 UPDATE。"""
        import inspect
        from app.services import user_memory_service
        source = inspect.getsource(user_memory_service.mark_used)
        # 应使用 .update({...col: col + 1...}) 模式
        assert "col + 1" in source or "use_count + 1" in source
        # 不应再使用 for 循环 +  += 1 模式
        assert "f.use_count += 1" not in source


class TestAtomicIncrementFunctional:
    """功能测试：单次调用计数正确。"""

    def test_atomic_increment_increases_count(self, db_session):
        """_atomic_increment 正确增加计数值。"""
        from app.models.experience_post import ExperiencePost
        from app.services.experience_post_service import _atomic_increment

        post = ExperiencePost(
            user_id=uuid4(),
            title="测试帖",
            content="测试内容",
            status="approved",
            view_count=0,
            like_count=0,
            comment_count=0,
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

        # 调用原子 +1
        ok = _atomic_increment(db_session, ExperiencePost, post.id, "view_count", 1)
        assert ok is True
        db_session.commit()

        # 重新查询验证
        db_session.expire_all()
        post2 = db_session.query(ExperiencePost).filter(ExperiencePost.id == post.id).first()
        assert post2.view_count == 1

    def test_atomic_increment_with_delta(self, db_session):
        """_atomic_increment 支持自定义 delta（如 +5）。"""
        from app.models.experience_post import ExperiencePost
        from app.services.experience_post_service import _atomic_increment

        post = ExperiencePost(
            user_id=uuid4(),
            title="测试帖",
            content="测试内容",
            status="approved",
            view_count=10,
            like_count=0,
            comment_count=0,
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

        ok = _atomic_increment(db_session, ExperiencePost, post.id, "view_count", 5)
        assert ok is True
        db_session.commit()
        db_session.expire_all()

        post2 = db_session.query(ExperiencePost).filter(ExperiencePost.id == post.id).first()
        assert post2.view_count == 15

    def test_atomic_increment_returns_false_for_nonexistent(self, db_session):
        """_atomic_increment 对不存在的 id 返回 False。"""
        from app.models.experience_post import ExperiencePost
        from app.services.experience_post_service import _atomic_increment

        ok = _atomic_increment(db_session, ExperiencePost, uuid4(), "view_count", 1)
        assert ok is False


class TestAtomicIncrementConcurrency:
    """并发测试：多线程并发调用不丢失更新。

    使用文件 SQLite + WAL 模式 + 独立连接（每线程一个 Session）模拟真实多 worker 并发。
    SQLite WAL 模式支持多读单写，写操作会自动加锁串行化，但每条 UPDATE 语句本身是原子的，
    所以能验证「原子 UPDATE」相对「read-modify-write」的优势：不会丢失更新。
    """
    def test_concurrent_increments_no_lost_update(self, tmp_path):
        """10 个线程各 +10，最终应 = 100（无丢失更新）。"""
        from sqlalchemy import create_engine, event
        from sqlalchemy.orm import sessionmaker

        from app.database import Base
        from app.models.experience_post import ExperiencePost
        from app.services.experience_post_service import _atomic_increment

        # 文件 SQLite + WAL 模式（支持多连接并发）
        db_file = tmp_path / "concurrent.db"
        engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def _set_wal(dbapi_conn, _):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        Base.metadata.create_all(engine)
        SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

        # 初始化一条记录
        session = SessionFactory()
        post = ExperiencePost(
            user_id=uuid4(),
            title="并发测试帖",
            content="测试内容",
            status="approved",
            view_count=0,
            like_count=0,
            comment_count=0,
        )
        session.add(post)
        session.commit()
        session.refresh(post)
        post_id = post.id
        session.close()

        # 并发：10 个线程，每个 +10
        NUM_THREADS = 10
        INCREMENT_PER_THREAD = 10
        errors: list[Exception] = []

        def worker():
            try:
                s = SessionFactory()
                try:
                    for _ in range(INCREMENT_PER_THREAD):
                        # 重试机制 — SQLite WAL 偶发 database is locked
                        for attempt in range(5):
                            try:
                                _atomic_increment(s, ExperiencePost, post_id, "view_count", 1)
                                s.commit()
                                break
                            except Exception:
                                s.rollback()
                                if attempt == 4:
                                    raise
                finally:
                    s.close()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(NUM_THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"并发执行出错: {errors}"

        # 验证最终值
        s = SessionFactory()
        try:
            final_post = s.query(ExperiencePost).filter(ExperiencePost.id == post_id).first()
            expected = NUM_THREADS * INCREMENT_PER_THREAD
            assert final_post.view_count == expected, (
                f"丢失更新: 期望 {expected}, 实际 {final_post.view_count}"
            )
        finally:
            s.close()
            Base.metadata.drop_all(engine)
            engine.dispose()


class TestServiceLayerAtomicIntegration:
    """服务层集成测试 — 验证公共 API 仍正确工作。"""

    def test_like_experience_post_increments_atomically(self, db_session):
        """like_experience_post 正确增加 like_count。"""
        from app.models.experience_post import ExperiencePost
        from app.services.experience_post_service import like_experience_post

        post = ExperiencePost(
            user_id=uuid4(),
            title="点赞测试",
            content="测试内容",
            status="approved",
            view_count=0,
            like_count=5,
            comment_count=0,
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

        result = like_experience_post(db_session, post.id)
        assert result is not None
        assert result.like_count == 6

    def test_increment_experience_post_view_increments(self, db_session):
        """increment_experience_post_view 正确增加 view_count。"""
        from app.models.experience_post import ExperiencePost
        from app.services.experience_post_service import increment_experience_post_view

        post = ExperiencePost(
            user_id=uuid4(),
            title="浏览测试",
            content="测试内容",
            status="approved",
            view_count=10,
            like_count=0,
            comment_count=0,
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

        ok = increment_experience_post_view(db_session, post.id)
        assert ok is True

        db_session.expire_all()
        post2 = db_session.query(ExperiencePost).filter(ExperiencePost.id == post.id).first()
        assert post2.view_count == 11

    def test_like_review_increments_atomically(self, db_session):
        """mentor_service.like_review 正确增加 like_count。"""
        from datetime import datetime, timezone

        from app.models.mentor import Mentor
        from app.models.mentor_review import MentorReview
        from app.services.mentor_service import like_review

        mentor = Mentor(
            name="测试导师",
            university="测试大学",
            department="测试系",
            title="教授",
        )
        db_session.add(mentor)
        db_session.commit()
        db_session.refresh(mentor)

        review = MentorReview(
            mentor_id=mentor.id,
            user_id=uuid4(),
            rating_academic=5,
            rating_guidance=5,
            rating_relationship=5,
            rating_funding=5,
            rating_workload=5,
            rating_career=5,
            overall_rating=5.0,
            title="好评",
            content="很好",
            review_status="approved",
            like_count=3,
            submitted_at=datetime.now(timezone.utc).isoformat(),
        )
        db_session.add(review)
        db_session.commit()
        db_session.refresh(review)

        result = like_review(db_session, review.id)
        assert result is not None
        assert result.like_count == 4
