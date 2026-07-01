# backend/tests/test_career_profile.py
"""用户职业画像 API 测试。"""
from app.models.career_profile import CareerProfile
from app.models.user import User


def _create_payload(**overrides):
    """构造创建画像的请求体，可覆盖部分字段。"""
    payload = {
        "education_level": "bachelor",
        "major": "计算机科学",
        "school_name": "清华大学",
        "school_tier": "985",
        "graduation_year": 2025,
        "target_direction": "大厂后端开发",
        "target_industry": "互联网",
        "technical_skill": 4,
        "communication_skill": 3,
        "leadership_skill": 2,
        "creativity_skill": 4,
        "self_introduction": "热爱编程的后端开发者",
    }
    payload.update(overrides)
    return payload


class TestCareerProfileCreate:
    def test_create_profile_201(self, auth_headers, client):
        """创建职业画像返回 201，字段全部正确回显。"""
        resp = client.post(
            "/api/career-profile",
            headers=auth_headers,
            json=_create_payload(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"]
        assert data["user_id"]
        assert data["education_level"] == "bachelor"
        assert data["major"] == "计算机科学"
        assert data["school_name"] == "清华大学"
        assert data["school_tier"] == "985"
        assert data["graduation_year"] == 2025
        assert data["target_direction"] == "大厂后端开发"
        assert data["target_industry"] == "互联网"
        assert data["technical_skill"] == 4
        assert data["communication_skill"] == 3
        assert data["leadership_skill"] == 2
        assert data["creativity_skill"] == 4
        assert data["self_introduction"] == "热爱编程的后端开发者"
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

    def test_create_profile_defaults(self, auth_headers, client):
        """未提供技能评分时使用默认值 3。"""
        resp = client.post(
            "/api/career-profile",
            headers=auth_headers,
            json={"major": "软件工程"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["technical_skill"] == 3
        assert data["communication_skill"] == 3
        assert data["leadership_skill"] == 3
        assert data["creativity_skill"] == 3

    def test_create_profile_duplicate_400(self, auth_headers, client):
        """重复创建返回 400。"""
        client.post(
            "/api/career-profile",
            headers=auth_headers,
            json={"major": "计算机科学"},
        )
        resp = client.post(
            "/api/career-profile",
            headers=auth_headers,
            json={"major": "软件工程"},
        )
        assert resp.status_code == 400
        assert "已存在" in resp.json()["detail"]


class TestCareerProfileGet:
    def test_get_profile_200(self, auth_headers, client):
        """已存在画像时 GET 返回 200 与画像数据。"""
        client.post(
            "/api/career-profile",
            headers=auth_headers,
            json=_create_payload(),
        )
        resp = client.get("/api/career-profile", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data is not None
        assert data["major"] == "计算机科学"
        assert data["target_direction"] == "大厂后端开发"

    def test_get_profile_null_when_not_exists(self, auth_headers, client):
        """不存在画像时 GET 返回 200 且 body 为 null。"""
        resp = client.get("/api/career-profile", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() is None


class TestCareerProfileUpdate:
    def test_update_profile_200(self, auth_headers, client):
        """更新画像返回 200，指定字段被更新。"""
        client.post(
            "/api/career-profile",
            headers=auth_headers,
            json=_create_payload(technical_skill=3, major="计算机科学"),
        )
        resp = client.put(
            "/api/career-profile",
            headers=auth_headers,
            json={"major": "软件工程", "technical_skill": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["major"] == "软件工程"
        assert data["technical_skill"] == 5

    def test_update_profile_preserves_unspecified_fields(self, auth_headers, client):
        """更新时未指定的字段保持原值（exclude_unset 语义）。"""
        client.post(
            "/api/career-profile",
            headers=auth_headers,
            json=_create_payload(
                communication_skill=4, leadership_skill=4, major="计算机科学"
            ),
        )
        resp = client.put(
            "/api/career-profile",
            headers=auth_headers,
            json={"major": "软件工程"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["major"] == "软件工程"
        # 未指定的技能评分应保持原值
        assert data["communication_skill"] == 4
        assert data["leadership_skill"] == 4

    def test_update_profile_404(self, auth_headers, client):
        """画像不存在时更新返回 404。"""
        resp = client.put(
            "/api/career-profile",
            headers=auth_headers,
            json={"major": "软件工程"},
        )
        assert resp.status_code == 404
        assert "不存在" in resp.json()["detail"]


class TestCareerProfileAuth:
    def test_unauthorized_get_401(self, client):
        """未认证 GET 返回 401。"""
        resp = client.get("/api/career-profile")
        assert resp.status_code == 401

    def test_unauthorized_post_401(self, client):
        """未认证 POST 返回 401。"""
        resp = client.post(
            "/api/career-profile",
            json={"major": "计算机科学"},
        )
        assert resp.status_code == 401

    def test_unauthorized_put_401(self, client):
        """未认证 PUT 返回 401。"""
        resp = client.put(
            "/api/career-profile",
            json={"major": "计算机科学"},
        )
        assert resp.status_code == 401
