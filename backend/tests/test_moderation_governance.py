# backend/tests/test_moderation_governance.py
"""社区治理测试（A5）— 举报 / 屏蔽 / 封禁 / 用户管理 / QA 审核。

覆盖：
- 举报：提交（未登录 401、不能举报自己、目标不存在 404、防刷 429）、
  管理员列表（状态/类型筛选）、处理（下架内容 / 驳回 / 联动封禁 /
  target=user 直接封禁 / 重复处理 409）、处理结果通知举报人
- 屏蔽：屏蔽 / 幂等 / 屏蔽自己 / 列表 / 取消
- 封禁：登录拒绝（401）、已登录请求立即 403（缓存路径）、解封恢复、
  不能封禁管理员、列表搜索与状态筛选、非管理员 403
- QA 审核：approve/reject 问题与回答
- moderation 回归：经验贴 approve/reject/pin（A3 修复：pending 不再 404）
"""

import uuid

import pytest

from app.models.experience_post import ExperiencePost
from app.models.notification import Notification
from app.models.post import Post, PostStatus
from app.models.qa import QA
from app.models.qa_answer import QAAnswer
from app.models.report import Report, ReportStatus
from app.models.user import User, UserStatus

# ======================================================================
# fixtures
# ======================================================================


@pytest.fixture
def admin_headers(client, db_session):
    from app.core.security import hash_password

    admin = User(
        email="admin@example.org",
        password_hash=hash_password("Admin1234!"),
        name="治理管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@example.org", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def second_user_headers(client, db_session):
    """第二个普通用户（被举报者 / 被屏蔽者 / 被封禁者）。"""
    resp = client.post(
        "/api/auth/register",
        json={"email": "user2@example.net", "password": "Test1234!", "name": "二号用户"},
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "user2@example.net", "password": "Test1234!"},
    )
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_post(client, headers, content="可举报的帖子内容"):
    return client.post(
        "/api/posts",
        headers=headers,
        json={"topic_type": "school_major", "topic_key": "清华大学|计算机", "content": content},
    )


def _create_experience_post(client, headers):
    return client.post(
        "/api/kaoyan/experience-posts",
        headers=headers,
        json={
            "title": "上岸经验帖",
            "content": "这是一篇需要审核的经验贴正文，包含足够长度。",
            "tags": ["考研"],
            "category": "general",
            "is_anonymous": False,
            "source_platform": "user",
        },
    )


def _create_qa(client, headers):
    return client.post(
        "/api/kaoyan/qa",
        headers=headers,
        json={"title": "考研问题", "content": "这是问题详情内容", "tags": ["考研"]},
    )


def _db_user(db_session, email):
    return db_session.query(User).filter(User.email == email).first()


# ======================================================================
# 举报提交
# ======================================================================


class TestReportSubmit:
    def test_submit_report_success(self, client, auth_headers, db_session):
        post = _create_post(client, auth_headers)
        assert post.status_code == 201
        post_id = post.json()["id"]

        resp = client.post(
            "/api/reports",
            headers=auth_headers,
            json={
                "target_type": "post",
                "target_id": post_id,
                "reason": "广告推广",
                "detail": "帖子内容为广告链接",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "pending"
        assert data["target_type"] == "post"
        assert data["reason"] == "广告推广"
        assert data["detail"] == "帖子内容为广告链接"

    def test_submit_report_requires_login(self, client, db_session):
        resp = client.post(
            "/api/reports",
            json={
                "target_type": "post",
                "target_id": str(uuid.uuid4()),
                "reason": "广告",
            },
        )
        assert resp.status_code in (401, 403)

    def test_cannot_report_self(self, client, auth_headers, db_session):
        me = _db_user(db_session, "test@example.com")
        resp = client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "user", "target_id": str(me.id), "reason": "骂我"},
        )
        assert resp.status_code == 400

    def test_report_nonexistent_target(self, client, auth_headers):
        resp = client.post(
            "/api/reports",
            headers=auth_headers,
            json={
                "target_type": "post",
                "target_id": str(uuid.uuid4()),
                "reason": "广告",
            },
        )
        assert resp.status_code == 404

    def test_report_rate_limited(self, client, auth_headers, db_session):
        """POST /api/reports 限流 5/min，第 6 次返回 429。"""
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        for _ in range(5):
            resp = client.post(
                "/api/reports",
                headers=auth_headers,
                json={"target_type": "post", "target_id": post_id, "reason": "刷屏"},
            )
            assert resp.status_code == 201

        resp6 = client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "post", "target_id": post_id, "reason": "刷屏"},
        )
        assert resp6.status_code == 429


# ======================================================================
# 管理员举报列表 / 处理
# ======================================================================


class TestAdminReports:
    def test_non_admin_cannot_list(self, client, auth_headers):
        resp = client.get("/api/admin/reports", headers=auth_headers)
        assert resp.status_code == 403

    def test_list_and_filter(self, client, auth_headers, admin_headers, db_session):
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]
        client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "post", "target_id": post_id, "reason": "广告"},
        )

        # 全部
        resp = client.get("/api/admin/reports", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        # 按状态筛选 pending
        resp = client.get("/api/admin/reports?status=pending", headers=admin_headers)
        assert resp.json()["total"] >= 1
        assert all(i["status"] == "pending" for i in resp.json()["items"])

        # 按类型筛选 post
        resp = client.get("/api/admin/reports?target_type=post", headers=admin_headers)
        assert resp.json()["total"] >= 1
        assert all(i["target_type"] == "post" for i in resp.json()["items"])

        # 按类型筛选 user（无数据时 total=0）
        resp = client.get("/api/admin/reports?target_type=user", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_process_processed_hides_post(self, client, auth_headers, admin_headers, db_session):
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]
        client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "post", "target_id": post_id, "reason": "人身攻击"},
        )
        report = db_session.query(Report).first()
        assert report is not None

        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed", "note": "核实属实，已下架"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "processed"

        # 帖子已被隐藏
        db_post = db_session.query(Post).filter(Post.id == post_id).first()
        assert db_post.status == PostStatus.hidden
        # 举报状态已更新
        db_session.refresh(report)
        assert report.status == ReportStatus.processed
        assert report.processed_note == "核实属实，已下架"

    def test_process_processed_notifies_reporter(
        self, client, second_user_headers, auth_headers, admin_headers, db_session
    ):
        # 作者与举报人分开（作者 user2 会收到"内容被下架"通知，
        # 举报人 test@example.com 只收到"举报处理结果"通知，避免排序歧义）
        post = _create_post(client, second_user_headers)
        post_id = post.json()["id"]
        client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "post", "target_id": post_id, "reason": "刷屏"},
        )
        reporter = _db_user(db_session, "test@example.com")
        report = db_session.query(Report).first()

        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed"},
        )
        assert resp.status_code == 200

        note = (
            db_session.query(Notification)
            .filter(Notification.user_id == reporter.id)
            .order_by(Notification.created_at.desc())
            .first()
        )
        assert note is not None
        assert note.type == "moderation"
        assert "举报" in note.title or "举报" in note.content

    def test_process_rejected_keeps_content(self, client, auth_headers, admin_headers, db_session):
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]
        client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "post", "target_id": post_id, "reason": "不实举报"},
        )
        report = db_session.query(Report).first()

        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "rejected", "note": "证据不足"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        # 内容保持可见
        db_post = db_session.query(Post).filter(Post.id == post_id).first()
        assert db_post.status == PostStatus.active
        db_session.refresh(report)
        assert report.status == ReportStatus.rejected

    def test_process_duplicate_conflict(self, client, auth_headers, admin_headers, db_session):
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]
        client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "post", "target_id": post_id, "reason": "广告"},
        )
        report = db_session.query(Report).first()
        client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "rejected"},
        )
        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed"},
        )
        assert resp.status_code == 409

    def test_process_ban_author_requires_reason(
        self, client, auth_headers, admin_headers, db_session
    ):
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]
        client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "post", "target_id": post_id, "reason": "违规"},
        )
        report = db_session.query(Report).first()

        # 联动封禁但未填原因 → 400
        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed", "ban_author": True},
        )
        assert resp.status_code == 400

    def test_process_ban_author_works(self, client, auth_headers, admin_headers, db_session):
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]
        client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "post", "target_id": post_id, "reason": "恶意刷屏"},
        )
        report = db_session.query(Report).first()

        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed", "ban_author": True, "ban_reason": "发布违规内容"},
        )
        assert resp.status_code == 200

        author = _db_user(db_session, "test@example.com")
        assert author.status == UserStatus.banned
        assert author.ban_reason == "发布违规内容"

    def test_process_user_target_bans_user(
        self, client, auth_headers, second_user_headers, admin_headers, db_session
    ):
        """举报对象为用户：处理即封禁，ban_reason 必填。"""
        target = _db_user(db_session, "user2@example.net")
        client.post(
            "/api/reports",
            headers=auth_headers,
            json={"target_type": "user", "target_id": str(target.id), "reason": "骚扰他人"},
        )
        report = db_session.query(Report).first()

        # 缺 ban_reason → 400（处置失败，举报保持 pending）
        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed"},
        )
        assert resp.status_code == 400

        # 带 ban_reason → 封禁成功
        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed", "ban_reason": "多次骚扰他人"},
        )
        assert resp.status_code == 200
        db_session.refresh(target)
        assert target.status == UserStatus.banned

    def test_process_reports_user_targets(
        self, client, second_user_headers, admin_headers, db_session
    ):
        """举报经验贴 / 评论 / 问答，处理后被置为 rejected 隐藏。"""
        # 经验贴
        ep = _create_experience_post(client, second_user_headers)
        ep_id = ep.json()["id"]
        client.post(
            "/api/reports",
            headers=second_user_headers,
            json={"target_type": "experience_post", "target_id": ep_id, "reason": "虚假内容"},
        )
        report = db_session.query(Report).filter(Report.target_type == "experience_post").first()
        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed"},
        )
        assert resp.status_code == 200
        db_ep = db_session.query(ExperiencePost).filter(ExperiencePost.id == ep_id).first()
        assert db_ep.status == "rejected"

        # 问答
        qa = _create_qa(client, second_user_headers)
        qa_id = qa.json()["id"]
        client.post(
            "/api/reports",
            headers=second_user_headers,
            json={"target_type": "qa", "target_id": qa_id, "reason": "违规提问"},
        )
        report = db_session.query(Report).filter(Report.target_type == "qa").first()
        resp = client.post(
            f"/api/admin/reports/{report.id}/process",
            headers=admin_headers,
            json={"action": "processed"},
        )
        assert resp.status_code == 200
        db_qa = db_session.query(QA).filter(QA.id == qa_id).first()
        assert db_qa.status == "rejected"


# ======================================================================
# 屏蔽
# ======================================================================


class TestBlockRelations:
    def test_block_and_list_and_unblock(
        self, client, auth_headers, second_user_headers, db_session
    ):
        target = _db_user(db_session, "user2@example.net")
        target_id = str(target.id)

        # 屏蔽
        resp = client.post(f"/api/users/{target_id}/block", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["blocked_id"] == target_id

        # 幂等：重复屏蔽成功
        resp = client.post(f"/api/users/{target_id}/block", headers=auth_headers)
        assert resp.status_code == 200

        # 列表
        resp = client.get("/api/users/me/blocks", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["name"] == "二号用户"

        # 取消
        resp = client.delete(f"/api/users/{target_id}/block", headers=auth_headers)
        assert resp.status_code == 200
        resp = client.get("/api/users/me/blocks", headers=auth_headers)
        assert resp.json()["total"] == 0

    def test_cannot_block_self(self, client, auth_headers, db_session):
        me = _db_user(db_session, "test@example.com")
        resp = client.post(f"/api/users/{me.id}/block", headers=auth_headers)
        assert resp.status_code == 400

    def test_block_requires_login(self, client, db_session):
        resp = client.post(f"/api/users/{uuid.uuid4()}/block")
        assert resp.status_code in (401, 403)

    def test_block_nonexistent_user(self, client, auth_headers):
        resp = client.post(f"/api/users/{uuid.uuid4()}/block", headers=auth_headers)
        assert resp.status_code == 404


# ======================================================================
# 封禁 / 解封 / 用户管理
# ======================================================================


class TestBanAndUserManagement:
    def test_ban_rejects_login(self, client, second_user_headers, admin_headers, db_session):
        target = _db_user(db_session, "user2@example.net")
        resp = client.post(
            f"/api/admin/users/{target.id}/ban",
            headers=admin_headers,
            json={"reason": "发布违规内容"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "banned"

        # 被封用户无法登录
        resp = client.post(
            "/api/auth/login",
            json={"email": "user2@example.net", "password": "Test1234!"},
        )
        assert resp.status_code == 401

    def test_ban_takes_effect_immediately(
        self, client, second_user_headers, admin_headers, db_session
    ):
        """已登录用户的 token 在封禁后立即 403（缓存路径也检查 status）。"""
        target = _db_user(db_session, "user2@example.net")
        # 预热 user 缓存
        resp = client.get("/api/auth/me", headers=second_user_headers)
        assert resp.status_code == 200

        resp = client.post(
            f"/api/admin/users/{target.id}/ban",
            headers=admin_headers,
            json={"reason": "违规"},
        )
        assert resp.status_code == 200

        # 缓存已失效 + _ensure_active → 立即 403
        resp = client.get("/api/auth/me", headers=second_user_headers)
        assert resp.status_code == 403

    def test_unban_restores_login(self, client, second_user_headers, admin_headers, db_session):
        target = _db_user(db_session, "user2@example.net")
        client.post(
            f"/api/admin/users/{target.id}/ban",
            headers=admin_headers,
            json={"reason": "违规"},
        )
        resp = client.post(
            f"/api/admin/users/{target.id}/unban",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

        resp = client.post(
            "/api/auth/login",
            json={"email": "user2@example.net", "password": "Test1234!"},
        )
        assert resp.status_code == 200

    def test_cannot_ban_admin(self, client, admin_headers, db_session):
        admin = _db_user(db_session, "admin@example.org")
        resp = client.post(
            f"/api/admin/users/{admin.id}/ban",
            headers=admin_headers,
            json={"reason": "测试"},
        )
        assert resp.status_code == 403

    def test_ban_requires_reason(self, client, second_user_headers, admin_headers, db_session):
        target = _db_user(db_session, "user2@example.net")
        resp = client.post(
            f"/api/admin/users/{target.id}/ban",
            headers=admin_headers,
            json={"reason": ""},
        )
        assert resp.status_code == 422

    def test_user_list_search_and_filter(
        self, client, auth_headers, second_user_headers, admin_headers, db_session
    ):
        # 关键词搜索
        resp = client.get("/api/admin/users?keyword=二号", headers=admin_headers)
        assert resp.status_code == 200
        names = [u["name"] for u in resp.json()["items"]]
        assert "二号用户" in names

        # 状态筛选：封禁一个用户后按 banned 筛选
        target = _db_user(db_session, "user2@example.net")
        client.post(
            f"/api/admin/users/{target.id}/ban",
            headers=admin_headers,
            json={"reason": "违规"},
        )
        resp = client.get("/api/admin/users?status=banned", headers=admin_headers)
        assert resp.status_code == 200
        assert all(u["status"] == "banned" for u in resp.json()["items"])
        assert any(u["email"] == "user2@example.net" for u in resp.json()["items"])

    def test_non_admin_cannot_access_user_admin(self, client, auth_headers):
        resp = client.get("/api/admin/users", headers=auth_headers)
        assert resp.status_code == 403
        resp = client.post(
            f"/api/admin/users/{uuid.uuid4()}/ban", headers=auth_headers, json={"reason": "x"}
        )
        assert resp.status_code == 403


# ======================================================================
# QA 审核 + moderation 回归（A3 修复）
# ======================================================================


class TestModerationRegression:
    def test_qa_approve_reject(self, client, auth_headers, admin_headers, db_session):
        qa = _create_qa(client, auth_headers)
        qa_id = qa.json()["id"]

        # 非管理员 403
        resp = client.post(f"/api/kaoyan/qa/{qa_id}/approve", headers=auth_headers)
        assert resp.status_code == 403

        # 管理员 approve（修复前 pending 问题会 404）
        resp = client.post(f"/api/kaoyan/qa/{qa_id}/approve", headers=admin_headers)
        assert resp.status_code == 200
        db_qa = db_session.query(QA).filter(QA.id == qa_id).first()
        assert db_qa.status == "approved"

        # 新问题 reject
        qa2 = _create_qa(client, auth_headers)
        qa2_id = qa2.json()["id"]
        resp = client.post(f"/api/kaoyan/qa/{qa2_id}/reject", headers=admin_headers)
        assert resp.status_code == 200
        db_qa2 = db_session.query(QA).filter(QA.id == qa2_id).first()
        assert db_qa2.status == "rejected"

    def test_qa_answer_approve_reject(
        self, client, auth_headers, second_user_headers, admin_headers, db_session
    ):
        qa = _create_qa(client, auth_headers)
        qa_id = qa.json()["id"]
        # 管理员先通过问题，再让二号用户回答
        client.post(f"/api/kaoyan/qa/{qa_id}/approve", headers=admin_headers)

        answer = client.post(
            f"/api/kaoyan/qa/{qa_id}/answers",
            headers=second_user_headers,
            json={"content": "这是一个回答内容"},
        )
        answer_id = answer.json()["id"]

        resp = client.post(f"/api/kaoyan/qa/answers/{answer_id}/approve", headers=admin_headers)
        assert resp.status_code == 200
        db_answer = db_session.query(QAAnswer).filter(QAAnswer.id == answer_id).first()
        assert db_answer.status == "approved"

        # 回答 reject
        answer2 = client.post(
            f"/api/kaoyan/qa/{qa_id}/answers",
            headers=second_user_headers,
            json={"content": "另一个回答"},
        )
        answer2_id = answer2.json()["id"]
        resp = client.post(f"/api/kaoyan/qa/answers/{answer2_id}/reject", headers=admin_headers)
        assert resp.status_code == 200
        db_answer2 = db_session.query(QAAnswer).filter(QAAnswer.id == answer2_id).first()
        assert db_answer2.status == "rejected"

    def test_experience_post_approve_reject_pin(
        self, client, auth_headers, admin_headers, db_session
    ):
        # approve（修复前 pending 帖 404）
        ep = _create_experience_post(client, auth_headers)
        ep_id = ep.json()["id"]
        assert ep.json()["status"] == "pending"

        resp = client.post(f"/api/kaoyan/experience-posts/{ep_id}/approve", headers=admin_headers)
        assert resp.status_code == 200
        db_ep = db_session.query(ExperiencePost).filter(ExperiencePost.id == ep_id).first()
        assert db_ep.status == "approved"

        # reject
        ep2 = _create_experience_post(client, auth_headers)
        ep2_id = ep2.json()["id"]
        resp = client.post(f"/api/kaoyan/experience-posts/{ep2_id}/reject", headers=admin_headers)
        assert resp.status_code == 200
        db_ep2 = db_session.query(ExperiencePost).filter(ExperiencePost.id == ep2_id).first()
        assert db_ep2.status == "rejected"

        # pin（修复前后端从未实现 setter，PATCH 恒 404）
        resp = client.post(
            f"/api/kaoyan/experience-posts/{ep_id}/pin",
            headers=admin_headers,
            json={"is_pinned": True},
        )
        assert resp.status_code == 200
        db_session.refresh(db_ep)
        assert db_ep.is_pinned is True

        resp = client.post(
            f"/api/kaoyan/experience-posts/{ep_id}/pin",
            headers=admin_headers,
            json={"is_pinned": False},
        )
        assert resp.status_code == 200
        db_session.refresh(db_ep)
        assert db_ep.is_pinned is False
