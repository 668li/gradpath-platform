"""评论系统 API 测试。"""
import pytest


class TestCommentCreate:
    def test_create_comment_success(self, client, auth_headers, db_session):
        """创建评论成功"""
        from app.models.experience_post import ExperiencePost
        from app.models.user import User

        user = db_session.query(User).first()
        post = ExperiencePost(
            title="测试帖子",
            content="测试内容",
            user_id=user.id,
        )
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

        resp = client.post(
            "/api/comments",
            headers=auth_headers,
            json={
                "post_id": str(post.id),
                "content": "这是一条测试评论",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "这是一条测试评论"
        assert data["post_id"] == str(post.id)

    def test_create_comment_unauthorized(self, client):
        """未登录创建评论应返回401"""
        resp = client.post(
            "/api/comments",
            json={
                "post_id": "00000000-0000-0000-0000-000000000000",
                "content": "测试评论",
            },
        )
        assert resp.status_code in [401, 403]

    def test_create_comment_invalid_post(self, client, auth_headers):
        """评论不存在的帖子应返回400"""
        resp = client.post(
            "/api/comments",
            headers=auth_headers,
            json={
                "post_id": "00000000-0000-0000-0000-000000000000",
                "content": "测试评论",
            },
        )
        assert resp.status_code == 400


class TestCommentList:
    def test_list_comments_empty(self, client, auth_headers, db_session):
        """帖子暂无评论时返回空列表"""
        from app.models.experience_post import ExperiencePost
        from app.models.user import User

        user = db_session.query(User).first()
        post = ExperiencePost(title="测试帖子", content="内容", user_id=user.id)
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

        resp = client.get(f"/api/comments/post/{post.id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestCommentNotification:
    def test_comment_triggers_notification_to_post_author(
        self, client, auth_headers, db_session
    ):
        """auth_headers 用户(评论者) 评论另一个用户(作者)的帖子后，作者收到通知"""
        from app.models.experience_post import ExperiencePost
        from app.models.user import User
        from app.models.notification import Notification

        # 评论者 = auth_headers 对应用户
        commenter = db_session.query(User).first()
        # 作者 = 另一个用户
        author = User(email="author2@example.com", name="作者", password_hash="x")
        db_session.add(author)
        db_session.commit()

        post = ExperiencePost(title="我的帖子标题", content="内容", user_id=author.id)
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

        # 评论者发表评论
        resp = client.post(
            "/api/comments",
            headers=auth_headers,
            json={"post_id": str(post.id), "content": "你好"},
        )
        assert resp.status_code == 201

        # 作者应收到通知（评论者 != 作者）
        notifs = db_session.query(Notification).filter_by(user_id=author.id).all()
        assert len(notifs) == 1
        assert notifs[0].type.value == "comment"
        assert "我的帖子" in notifs[0].content


class TestCommentLike:
    def test_like_comment(self, client, auth_headers, db_session):
        """点赞评论成功"""
        from app.models.experience_post import ExperiencePost
        from app.models.user import User
        from app.models.comment import Comment

        user = db_session.query(User).first()
        post = ExperiencePost(title="帖子", content="内容", user_id=user.id)
        db_session.add(post)
        db_session.commit()
        db_session.refresh(post)

        comment = Comment(
            post_id=post.id,
            user_id=user.id,
            content="待点赞评论",
        )
        db_session.add(comment)
        db_session.commit()
        db_session.refresh(comment)

        resp = client.post(f"/api/comments/{comment.id}/like", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "like_count" in data

    def test_like_comment_not_found(self, client, auth_headers):
        """点赞不存在的评论应返回404"""
        resp = client.post(
            "/api/comments/00000000-0000-0000-0000-000000000000/like",
            headers=auth_headers,
        )
        assert resp.status_code == 404
