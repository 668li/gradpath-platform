# backend/tests/test_knowledge.py
"""知识库 API 测试 — Phase 11。"""
import uuid

import pytest

from app.models.knowledge_article import KnowledgeArticle
from app.models.user import User


@pytest.fixture
def admin_headers(client, db_session):
    from app.core.security import hash_password

    admin = User(
        email="admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_articles(db_session, count=5, category="industry_guide"):
    """预置若干知识条目。"""
    for i in range(count):
        db_session.add(
            KnowledgeArticle(
                category=category,
                title=f"测试文章_{i}",
                content=f"这是第 {i} 篇测试文章内容，包含关键词 Python",
                tags=[f"标签{i % 2}", "Python"],
                source="test",
                metadata_={"index": i},
            )
        )
    db_session.commit()


class TestKnowledgeList:
    def test_list_articles_200(self, auth_headers, client, db_session):
        """列表查询返回 200。"""
        _seed_articles(db_session, count=3)
        resp = client.get("/api/knowledge", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

    def test_list_pagination(self, auth_headers, client, db_session):
        """分页参数生效。"""
        _seed_articles(db_session, count=5)
        resp = client.get(
            "/api/knowledge?page=1&page_size=2", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert len(data["items"]) == 2
        assert data["total"] >= 5

    def test_category_filter(self, auth_headers, client, db_session):
        """分类过滤生效。"""
        _seed_articles(db_session, count=3, category="industry_guide")
        _seed_articles(db_session, count=2, category="job_requirement")
        resp = client.get(
            "/api/knowledge?category=job_requirement", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        for item in data["items"]:
            assert item["category"] == "job_requirement"

    def test_list_requires_auth(self, client):
        """未登录返回 401。"""
        resp = client.get("/api/knowledge")
        assert resp.status_code == 401


class TestKnowledgeDetail:
    def test_get_article_200(self, auth_headers, client, db_session):
        """获取详情返回 200。"""
        _seed_articles(db_session, count=1)
        article = db_session.query(KnowledgeArticle).first()
        resp = client.get(f"/api/knowledge/{article.id}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["title"] == article.title

    def test_get_article_404(self, auth_headers, client):
        """不存在的 ID 返回 404。"""
        resp = client.get(f"/api/knowledge/{uuid.uuid4()}", headers=auth_headers)
        assert resp.status_code == 404


class TestKnowledgeSearch:
    def test_search_returns_relevant(self, auth_headers, client, db_session):
        """搜索返回相关结果。"""
        db_session.add(
            KnowledgeArticle(
                category="job_requirement",
                title="后端开发工程师岗位要求",
                content="精通 Java 或 Go 语言，熟悉 MySQL 和 Redis",
                tags=["后端", "Java"],
            )
        )
        db_session.add(
            KnowledgeArticle(
                category="industry_guide",
                title="互联网行业指南",
                content="互联网公司校招流程与薪资",
                tags=["互联网"],
            )
        )
        db_session.commit()

        resp = client.post(
            "/api/knowledge/search",
            headers=auth_headers,
            json={"query": "后端开发"},
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) >= 1
        # 标题命中的应排在前面
        assert "后端" in results[0]["title"]


class TestKnowledgeAdminCRUD:
    def test_create_admin_201(self, admin_headers, client):
        """管理员创建返回 201。"""
        resp = client.post(
            "/api/knowledge",
            headers=admin_headers,
            json={
                "category": "industry_guide",
                "title": "新建文章",
                "content": "测试内容",
                "tags": ["测试"],
                "metadata_": {"key": "value"},
            },
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "新建文章"
        assert resp.json()["category"] == "industry_guide"

    def test_create_non_admin_403(self, auth_headers, client):
        """非管理员创建返回 403。"""
        resp = client.post(
            "/api/knowledge",
            headers=auth_headers,
            json={
                "category": "industry_guide",
                "title": "新建文章",
                "content": "测试内容",
            },
        )
        assert resp.status_code == 403

    def test_update_admin_200(self, admin_headers, client, db_session):
        """管理员更新返回 200。"""
        _seed_articles(db_session, count=1)
        article = db_session.query(KnowledgeArticle).first()
        resp = client.put(
            f"/api/knowledge/{article.id}",
            headers=admin_headers,
            json={"title": "更新后的标题"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "更新后的标题"

    def test_delete_admin_204(self, admin_headers, client, db_session):
        """管理员删除返回 204。"""
        _seed_articles(db_session, count=1)
        article = db_session.query(KnowledgeArticle).first()
        resp = client.delete(
            f"/api/knowledge/{article.id}", headers=admin_headers
        )
        assert resp.status_code == 204
        # 确认已删除
        assert db_session.query(KnowledgeArticle).count() == 0

    def test_delete_non_admin_403(self, auth_headers, client, db_session):
        """非管理员删除返回 403。"""
        _seed_articles(db_session, count=1)
        article = db_session.query(KnowledgeArticle).first()
        resp = client.delete(
            f"/api/knowledge/{article.id}", headers=auth_headers
        )
        assert resp.status_code == 403
