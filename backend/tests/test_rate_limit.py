# backend/tests/test_rate_limit.py
"""限流测试（Task 3）。

注意：测试客户端 IP 默认为 "testclient"，所有请求共享同一限流键。
conftest 中的 autouse fixture 会在每个测试前后调用 limiter.reset()，
保证各测试从干净的限流状态开始。
"""
import uuid

from fastapi.testclient import TestClient

from app.main import app


def _login_payload(email: str = "nobody@test.com", password: str = "Wrong1!") -> dict:
    return {"email": email, "password": password}


def test_login_rate_limit(client: TestClient):
    """login 限流 5/分钟：第 6 次返回 429。"""
    statuses = []
    for _ in range(6):
        resp = client.post("/api/auth/login", json=_login_payload())
        statuses.append(resp.status_code)
    # 前 5 次允许通过（凭据错误返回 401）
    assert statuses[:5] == [401] * 5
    # 第 6 次被限流
    assert statuses[5] == 429


def test_register_rate_limit(client: TestClient):
    """register 限流 3/分钟：第 4 次返回 429。"""
    statuses = []
    for _ in range(4):
        email = f"ratelimit-{uuid.uuid4().hex[:8]}@test.com"
        resp = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "Abcdefg1!",
                "name": "限流测试用户",
            },
        )
        statuses.append(resp.status_code)
    # 前 3 次注册成功
    assert statuses[:3] == [201] * 3
    # 第 4 次被限流
    assert statuses[3] == 429


def test_ai_endpoint_rate_limit(client: TestClient, auth_headers: dict):
    """AI decision-advice 限流 10/分钟：第 11 次返回 429。"""
    statuses = []
    for _ in range(11):
        resp = client.post(
            "/api/ai/decision-advice",
            json={"destination_type": "employment"},
            headers=auth_headers,
        )
        statuses.append(resp.status_code)
    # 前 10 次允许通过（未配置 LLM 密钥 → 503）
    assert all(s in (503, 504) for s in statuses[:10]), statuses[:10]
    # 第 11 次被限流
    assert statuses[10] == 429


def test_rate_limit_response_has_headers(client: TestClient):
    """限流响应应包含 Retry-After 或 X-RateLimit-* 头。"""
    for _ in range(6):
        resp = client.post("/api/auth/login", json=_login_payload())
    assert resp.status_code == 429
    lowered = {k.lower() for k in resp.headers.keys()}
    assert "retry-after" in lowered or any(
        k.startswith("x-ratelimit-") for k in lowered
    ), f"missing rate limit headers: {dict(resp.headers)}"


def test_different_endpoints_have_independent_limits(client: TestClient):
    """不同端点的限流相互独立：耗尽 login 额度后 register 仍可用。"""
    # 耗尽 login 限流（5/分钟），第 6 次 429
    for _ in range(6):
        login_resp = client.post("/api/auth/login", json=_login_payload())
    assert login_resp.status_code == 429

    # register 限流独立，仍可正常注册
    email = f"independent-{uuid.uuid4().hex[:8]}@test.com"
    reg_resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "Abcdefg1!", "name": "独立限流"},
    )
    assert reg_resp.status_code == 201
