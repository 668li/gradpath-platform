# backend/tests/test_public_exposure_guard.py
"""M1 未审核不可读守卫 — 公开端点不得泄漏未审核/离题内容。

背景（09-02 主题门禁审计）：公共列表端点曾接受用户可控的 status 参数，
传 status=pending/rejected 即可绕过 approved 过滤与 is_off_topic 硬过滤，
匿名枚举全部未审核与离题内容。本文件固化修复后的底线：
- 匿名（或非管理员）请求 status != approved → 403
- 管理员可查 pending/rejected（管理审核页依赖）
- 默认列表只含 approved 且非离题内容
覆盖面：经验贴列表（offset/cursor 两分支）+ QA 列表。
"""

import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.experience_post import ExperiencePost
from app.models.qa import QA
from app.models.user import User


@pytest.fixture
def admin_headers(client, db_session):
    admin = User(
        email="guard-admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="守卫管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "guard-admin@test.com", "password": "Admin1234!"},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _seed_mixed_posts(db: Session, user_id) -> None:
    """三种状态 × 离题标记的组合，验证默认列表的可见性边界。"""
    posts = [
        ExperiencePost(
            user_id=user_id, title="approved正常帖", content="考研复试经验",
            status="approved", source_platform="user",
        ),
        ExperiencePost(
            user_id=user_id, title="approved但离题帖", content="这是游戏视频",
            status="approved", is_off_topic=True, topic_reason="命中离题词「三角洲」",
            source_platform="bilibili",
        ),
        ExperiencePost(
            user_id=user_id, title="pending待审帖", content="待审核内容",
            status="pending", source_platform="user",
        ),
        ExperiencePost(
            user_id=user_id, title="rejected被驳帖", content="被驳回内容",
            status="rejected", source_platform="user",
        ),
    ]
    db.add_all(posts)
    db.commit()


@pytest.fixture
def any_user(db_session) -> User:
    user = User(
        email="guard-author@test.com",
        password_hash=hash_password("Author1234!"),
        name="楼主",
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestExperiencePostsStatusGate:
    """经验贴列表：status 非 approved 收归管理员。"""

    def test_anonymous_pending_forbidden(self, client, db_session, any_user):
        _seed_mixed_posts(db_session, any_user.id)
        resp = client.get("/api/kaoyan/experience-posts", params={"status": "pending"})
        assert resp.status_code == 403

    def test_anonymous_rejected_forbidden(self, client, db_session, any_user):
        resp = client.get("/api/kaoyan/experience-posts", params={"status": "rejected"})
        assert resp.status_code == 403

    def test_cursor_branch_same_guard(self, client, db_session, any_user):
        """cursor 分支同样受保护（同一端点两分页路径都要堵）。"""
        resp = client.get(
            "/api/kaoyan/experience-posts",
            params={"status": "pending", "cursor": "x", "page_size": 5},
        )
        assert resp.status_code == 403

    def test_admin_can_list_pending(self, client, db_session, any_user, admin_headers):
        _seed_mixed_posts(db_session, any_user.id)
        resp = client.get(
            "/api/kaoyan/experience-posts", params={"status": "pending"}, headers=admin_headers
        )
        assert resp.status_code == 200
        titles = [item["title"] for item in resp.json()["items"]]
        assert "pending待审帖" in titles

    def test_default_list_hides_unapproved_and_off_topic(
        self, client, db_session, any_user
    ):
        _seed_mixed_posts(db_session, any_user.id)
        resp = client.get("/api/kaoyan/experience-posts")
        assert resp.status_code == 200
        titles = [item["title"] for item in resp.json()["items"]]
        assert "approved正常帖" in titles
        assert "pending待审帖" not in titles
        assert "rejected被驳帖" not in titles
        # S1 硬过滤：离题帖即便 approved 也不可见
        assert "approved但离题帖" not in titles

    def test_non_admin_user_pending_forbidden(self, client, db_session, any_user):
        """普通登录用户同样不可越权（只有管理员放行）。"""
        resp = client.post(
            "/api/auth/login",
            json={"email": "guard-author@test.com", "password": "Author1234!"},
        )
        headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}
        r = client.get(
            "/api/kaoyan/experience-posts", params={"status": "pending"}, headers=headers
        )
        assert r.status_code == 403


class TestQAStatusGate:
    """QA 列表：同病同堵（moderation 页 QA tab 依赖 status=pending）。"""

    def _seed_pending_qa(self, db: Session, user_id) -> None:
        db.add(
            QA(
                user_id=user_id,
                title="待审问题",
                content="这个问题的内容",
                tags=["复试"],
                status="pending",
            )
        )
        db.commit()

    def test_anonymous_pending_forbidden(self, client, db_session, any_user):
        self._seed_pending_qa(db_session, any_user.id)
        resp = client.get("/api/kaoyan/qa", params={"status": "pending"})
        assert resp.status_code == 403

    def test_admin_can_list_pending(self, client, db_session, any_user, admin_headers):
        self._seed_pending_qa(db_session, any_user.id)
        resp = client.get("/api/kaoyan/qa", params={"status": "pending"}, headers=admin_headers)
        assert resp.status_code == 200
        titles = [item["title"] for item in resp.json()["items"]]
        assert "待审问题" in titles

    def test_default_list_only_approved(self, client, db_session, any_user):
        self._seed_pending_qa(db_session, any_user.id)
        db_session.add(
            QA(
                user_id=any_user.id,
                title="已过审问题",
                content="正常内容",
                tags=[],
                status="approved",
            )
        )
        db_session.commit()
        resp = client.get("/api/kaoyan/qa")
        assert resp.status_code == 200
        titles = [item["title"] for item in resp.json()["items"]]
        assert "已过审问题" in titles
        assert "待审问题" not in titles
