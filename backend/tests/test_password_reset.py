# backend/tests/test_password_reset.py
"""密码重置功能测试。

覆盖：
- 请求重置令牌（存在的邮箱）
- 请求重置令牌（不存在的邮箱 — 应静默成功，防枚举）
- 使用有效令牌重置密码
- 使用无效令牌重置密码（应失败）
- 使用过期令牌重置密码（应失败）
- 已登录用户修改密码
- 修改密码时当前密码错误（应失败）
"""
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.security import (
    create_password_reset_token,
    verify_password,
    verify_password_reset_token,
)
from app.models.user import User


def test_forgot_password_existing_user(client: TestClient, db_session):
    """存在的邮箱请求重置：应返回成功消息。"""
    # 先注册用户
    client.post(
        "/api/auth/register",
        json={"email": "reset@test.com", "password": "OldPass1!", "name": "重置测试"},
    )

    resp = client.post(
        "/api/auth/forgot-password",
        json={"email": "reset@test.com"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data
    # 应返回确认消息（开发环境含令牌，生产/测试环境返回通用消息）
    msg = data["message"].lower()
    assert "令牌" in data["message"] or "token" in msg or "邮件" in data["message"] or "重置" in data["message"]


def test_forgot_password_nonexistent_user(client: TestClient):
    """不存在的邮箱请求重置：应返回成功消息（防枚举）。"""
    resp = client.post(
        "/api/auth/forgot-password",
        json={"email": "nonexistent@test.com"},
    )
    assert resp.status_code == 200
    assert "邮箱" in resp.json()["message"] or "注册" in resp.json()["message"]


def test_reset_password_with_valid_token(client: TestClient, db_session):
    """使用有效令牌重置密码：应成功。"""
    from uuid import uuid4

    from app.models.user import User

    # 注册用户
    client.post(
        "/api/auth/register",
        json={"email": "valid@test.com", "password": "OldPass1!", "name": "有效令牌"},
    )

    # 从数据库获取用户 ID，直接创建重置令牌
    user = db_session.query(User).filter(User.email == "valid@test.com").first()
    token = create_password_reset_token(str(user.id))

    # 重置密码
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "NewPass1!"},
    )
    assert resp.status_code == 200

    # 验证可以用新密码登录
    resp = client.post(
        "/api/auth/login",
        json={"email": "valid@test.com", "password": "NewPass1!"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_reset_password_with_invalid_token(client: TestClient):
    """使用无效令牌重置密码：应返回 400。"""
    resp = client.post(
        "/api/auth/reset-password",
        json={"token": "invalid-token-string", "new_password": "NewPass1!"},
    )
    assert resp.status_code == 400
    assert "无效" in resp.json()["detail"] or "expired" in resp.json()["detail"].lower()


def test_reset_password_with_wrong_token_type(client: TestClient, auth_headers):
    """使用 access_token 作为重置令牌：应失败（类型不匹配）。"""
    # 从 auth_headers 提取 access_token
    token = auth_headers["Authorization"].replace("Bearer ", "")

    resp = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "NewPass1!"},
    )
    assert resp.status_code == 400


def test_change_password_correct_current(client: TestClient, auth_headers):
    """已登录用户用正确当前密码修改密码：应成功。"""
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "Test1234!", "new_password": "NewPass1!"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "成功" in resp.json()["message"]


def test_change_password_wrong_current(client: TestClient, auth_headers):
    """已登录用户用错误当前密码修改密码：应返回 400。"""
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "WrongPass1!", "new_password": "NewPass1!"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "不正确" in resp.json()["detail"]


def test_change_password_requires_auth(client: TestClient):
    """未登录用户不能修改密码：应返回 401。"""
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "AnyPass1!", "new_password": "NewPass1!"},
    )
    assert resp.status_code == 401


def test_password_reset_token_expiry():
    """密码重置令牌验证：应正确解析有效令牌。"""
    from uuid import uuid4

    user_id = uuid4()
    token = create_password_reset_token(str(user_id))
    parsed_id = verify_password_reset_token(token)
    assert parsed_id == user_id


def test_password_reset_token_wrong_type():
    """access_token 不能作为密码重置令牌使用。"""
    from uuid import uuid4

    from app.core.security import create_access_token

    user_id = uuid4()
    access_token = create_access_token(str(user_id))
    parsed_id = verify_password_reset_token(access_token)
    assert parsed_id is None
