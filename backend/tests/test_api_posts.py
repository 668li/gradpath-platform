"""讨论帖 API 测试。"""
import pytest

TOPIC_SCHOOL = "清华大学|计算机科学与技术"
TOPIC_COMPANY = "腾讯|后端开发"


def _create_post(client, headers, topic_type="school_major",
                 topic_key=TOPIC_SCHOOL, content="测试帖子内容",
                 parent_id=None):
    """通过 API 发帖，返回响应。"""
    payload = {
        "topic_type": topic_type,
        "topic_key": topic_key,
        "content": content,
        "parent_id": parent_id,
    }
    return client.post("/api/posts", headers=headers, json=payload)


# ======================================================================
# 发帖
# ======================================================================

class TestCreatePost:
    def test_create_top_level_post(self, auth_headers, client):
        """创建顶层帖成功。"""
        resp = _create_post(client, auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["topic_type"] == "school_major"
        assert data["topic_key"] == TOPIC_SCHOOL
        assert data["content"] == "测试帖子内容"
        assert data["author_name"] == "测试用户"
        assert data["parent_id"] is None
        assert data["replies"] == []
        assert "id" in data
        assert "created_at" in data

    def test_create_reply(self, auth_headers, client):
        """回复顶层帖成功。"""
        top = _create_post(client, auth_headers)
        top_id = top.json()["id"]

        resp = _create_post(client, auth_headers, content="这是一条回复",
                            parent_id=top_id)
        assert resp.status_code == 201
        data = resp.json()
        assert data["parent_id"] == top_id
        assert data["content"] == "这是一条回复"

    def test_create_post_empty_content(self, auth_headers, client):
        """空内容发帖返回 422。"""
        resp = _create_post(client, auth_headers, content="")
        assert resp.status_code == 422

    def test_create_post_too_long(self, auth_headers, client):
        """超过 2000 字返回 422。"""
        resp = _create_post(client, auth_headers, content="x" * 2001)
        assert resp.status_code == 422

    def test_reply_nonexistent_parent(self, auth_headers, client):
        """回复不存在的父帖返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = _create_post(client, auth_headers, parent_id=fake_id)
        assert resp.status_code == 404

    def test_reply_topic_mismatch(self, auth_headers, client):
        """回复帖 topic 与父帖不一致返回 422。"""
        top = _create_post(client, auth_headers)
        top_id = top.json()["id"]

        resp = _create_post(client, auth_headers,
                            topic_key="其他学校|其他专业",
                            parent_id=top_id)
        assert resp.status_code == 422

    def test_reply_to_reply_rejected(self, auth_headers, client):
        """回复回复帖（多级嵌套）返回 422。"""
        top = _create_post(client, auth_headers)
        top_id = top.json()["id"]
        reply = _create_post(client, auth_headers, parent_id=top_id,
                             content="第一条回复")
        reply_id = reply.json()["id"]

        resp = _create_post(client, auth_headers, parent_id=reply_id,
                            content="回复回复")
        assert resp.status_code == 422

    def test_anonymous_create_fails(self, client):
        """未登录不能发帖。"""
        resp = _create_post(client, {}, )
        assert resp.status_code == 401


# ======================================================================
# 列表查询
# ======================================================================

class TestListPosts:
    def test_list_posts_with_replies(self, auth_headers, client):
        """列表返回顶层帖及其回复。"""
        top1 = _create_post(client, auth_headers, content="第一个帖子")
        top2 = _create_post(client, auth_headers, content="第二个帖子")
        reply = _create_post(client, auth_headers, content="回复第一个",
                             parent_id=top1.json()["id"])

        resp = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # 按创建时间降序，top2 在前
        first = data["items"][0]
        assert first["content"] == "第二个帖子"
        assert first["replies"] == []

        second = data["items"][1]
        assert second["content"] == "第一个帖子"
        assert len(second["replies"]) == 1
        assert second["replies"][0]["content"] == "回复第一个"

    def test_list_posts_empty(self, client):
        """无帖时返回空列表。"""
        resp = client.get(
            "/api/posts",
            params={"topic_type": "company_position",
                    "topic_key": "字节跳动|算法工程师"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_posts_pagination(self, auth_headers, client):
        """分页：page_size=1 时每页 1 条。"""
        for i in range(3):
            _create_post(client, auth_headers, content=f"帖子{i}")

        resp = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL,
                    "page": 1, "page_size": 1},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["page_size"] == 1

    def test_list_no_auth_required(self, client):
        """列表查询不需要登录。"""
        resp = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL},
        )
        assert resp.status_code == 200


# ======================================================================
# 编辑
# ======================================================================

class TestUpdatePost:
    def test_update_own_post(self, auth_headers, client):
        """编辑自己的帖子。"""
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        resp = client.put(
            f"/api/posts/{post_id}",
            headers=auth_headers,
            json={"content": "修改后的内容"},
        )
        assert resp.status_code == 200
        assert resp.json()["content"] == "修改后的内容"

    def test_update_others_post(self, auth_headers, client):
        """不能编辑他人帖子（403）。"""
        # 用第一个账号发帖
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        # 注册第二个账号
        client.post(
            "/api/auth/register",
            json={"email": "other@example.com", "password": "Test1234!",
                  "name": "其他用户"},
        )
        resp_login = client.post(
            "/api/auth/login",
            json={"email": "other@example.com", "password": "Test1234!"},
        )
        other_headers = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}

        resp = client.put(
            f"/api/posts/{post_id}",
            headers=other_headers,
            json={"content": "恶意修改"},
        )
        assert resp.status_code == 403

    def test_update_nonexistent(self, auth_headers, client):
        """编辑不存在的帖子返回 404。"""
        fake_id = "00000000-0000-0000-0000-000000000000"
        resp = client.put(
            f"/api/posts/{fake_id}",
            headers=auth_headers,
            json={"content": "内容"},
        )
        assert resp.status_code == 404


# ======================================================================
# 删除
# ======================================================================

class TestDeletePost:
    def test_delete_own_post(self, auth_headers, client):
        """删除自己的帖子。"""
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        resp = client.delete(f"/api/posts/{post_id}", headers=auth_headers)
        assert resp.status_code == 204

        # 确认已删除
        resp_list = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL},
        )
        assert resp_list.json()["total"] == 0

    def test_cascade_delete(self, auth_headers, client):
        """删除顶层帖级联删除所有回复。"""
        top = _create_post(client, auth_headers)
        top_id = top.json()["id"]
        _create_post(client, auth_headers, parent_id=top_id, content="回复1")
        _create_post(client, auth_headers, parent_id=top_id, content="回复2")

        # 删除顶层帖
        resp = client.delete(f"/api/posts/{top_id}", headers=auth_headers)
        assert resp.status_code == 204

        # 确认帖子和回复都被删除
        resp_list = client.get(
            "/api/posts",
            params={"topic_type": "school_major", "topic_key": TOPIC_SCHOOL},
        )
        assert resp_list.json()["total"] == 0

    def test_delete_others_post(self, auth_headers, client):
        """不能删除他人帖子（403）。"""
        post = _create_post(client, auth_headers)
        post_id = post.json()["id"]

        # 注册第二个账号
        client.post(
            "/api/auth/register",
            json={"email": "other2@example.com", "password": "Test1234!",
                  "name": "其他用户2"},
        )
        resp_login = client.post(
            "/api/auth/login",
            json={"email": "other2@example.com", "password": "Test1234!"},
        )
        other_headers = {"Authorization": f"Bearer {resp_login.json()['access_token']}"}

        resp = client.delete(f"/api/posts/{post_id}", headers=other_headers)
        assert resp.status_code == 403
