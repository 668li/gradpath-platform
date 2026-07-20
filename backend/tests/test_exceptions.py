# backend/tests/test_exceptions.py
"""全局异常处理器测试（C2 改造后）。"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.exceptions import (
    BusinessError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitExceededError,
    ValidationFailedError,
)
from app.main import app


@pytest.fixture
def exc_client():
    """注册临时路由用于触发各类异常，并在测试后清理。

    使用 raise_server_exceptions=False，以便观测兜底 Exception 处理器返回的 500
    响应（ServerErrorMiddleware 在调用处理器后总会重新抛出原异常，默认 TestClient
    会将其再次抛出从而无法拿到响应体）。
    """
    added_routes = []

    def raise_business() -> dict:
        raise BusinessError()

    def raise_business_custom() -> dict:
        raise BusinessError("CUSTOM_ERROR", "自定义业务错误消息")

    def raise_business_with_details() -> dict:
        raise BusinessError(
            "QUOTA_EXCEEDED", "AI 调用次数已用尽", 429,
            details={"quota": 100, "used": 100},
        )

    def raise_not_found() -> dict:
        raise NotFoundError()

    def raise_forbidden() -> dict:
        raise ForbiddenError()

    def raise_validation() -> dict:
        raise ValidationFailedError(details={"field": "email", "issue": "invalid"})

    def raise_rate_limit() -> dict:
        raise RateLimitExceededError()

    def raise_conflict() -> dict:
        raise ConflictError("该邮箱已注册")

    def raise_unexpected() -> dict:
        # 故意携带"敏感信息"，验证不会泄露到响应体
        raise RuntimeError("内部敏感信息不应泄露")

    def raise_http_404() -> dict:
        raise HTTPException(status_code=404, detail="找不到该资源")

    routes = {
        "/_test/business": raise_business,
        "/_test/business-custom": raise_business_custom,
        "/_test/business-details": raise_business_with_details,
        "/_test/not-found": raise_not_found,
        "/_test/forbidden": raise_forbidden,
        "/_test/validation": raise_validation,
        "/_test/rate-limit": raise_rate_limit,
        "/_test/conflict": raise_conflict,
        "/_test/unexpected": raise_unexpected,
        "/_test/http-404": raise_http_404,
    }
    for path, func in routes.items():
        app.add_api_route(path, func, methods=["GET"])
        added_routes.append(app.router.routes[-1])

    yield TestClient(app, raise_server_exceptions=False)

    # 清理临时路由，避免污染其他测试
    for route in added_routes:
        if route in app.router.routes:
            app.router.routes.remove(route)


def test_business_error_returns_400(exc_client):
    """BusinessError 默认返回 400 与统一格式。"""
    resp = exc_client.get("/_test/business")
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "BUSINESS_ERROR"
    assert body["message"] == "业务错误"
    assert body["details"] == {}
    # 兼容字段
    assert body["detail"] == "业务错误"


def test_business_error_with_custom_code(exc_client):
    """BusinessError 携带自定义 code/message 时正确返回。"""
    resp = exc_client.get("/_test/business-custom")
    assert resp.status_code == 400
    body = resp.json()
    assert body["code"] == "CUSTOM_ERROR"
    assert body["message"] == "自定义业务错误消息"


def test_business_error_with_details(exc_client):
    """BusinessError 携带 details 时透传到响应。"""
    resp = exc_client.get("/_test/business-details")
    assert resp.status_code == 429
    body = resp.json()
    assert body["code"] == "QUOTA_EXCEEDED"
    assert body["details"] == {"quota": 100, "used": 100}


def test_not_found_error_returns_404(exc_client):
    """NotFoundError 返回 404 与 NOT_FOUND code。"""
    resp = exc_client.get("/_test/not-found")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "NOT_FOUND"
    assert body["message"] == "资源不存在"


def test_forbidden_error_returns_403(exc_client):
    """ForbiddenError 返回 403。"""
    resp = exc_client.get("/_test/forbidden")
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "FORBIDDEN"


def test_validation_error_returns_422(exc_client):
    """ValidationFailedError 返回 422 与 details。"""
    resp = exc_client.get("/_test/validation")
    assert resp.status_code == 422
    body = resp.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert body["details"]["field"] == "email"


def test_rate_limit_error_returns_429(exc_client):
    """RateLimitExceededError 返回 429。"""
    resp = exc_client.get("/_test/rate-limit")
    assert resp.status_code == 429
    body = resp.json()
    assert body["code"] == "RATE_LIMIT_EXCEEDED"


def test_conflict_error_returns_409(exc_client):
    """ConflictError 返回 409。"""
    resp = exc_client.get("/_test/conflict")
    assert resp.status_code == 409
    body = resp.json()
    assert body["code"] == "CONFLICT"
    assert body["message"] == "该邮箱已注册"


def test_unhandled_exception_returns_500_without_detail(exc_client):
    """未处理异常返回 500 且不泄露内部错误。"""
    resp = exc_client.get("/_test/unexpected")
    assert resp.status_code == 500
    body = resp.json()
    assert body["code"] == "INTERNAL_ERROR"
    assert body["message"] == "服务器内部错误"
    # 确保真正的异常信息没有泄露
    assert "内部敏感信息" not in resp.text


def test_http_exception_still_works(exc_client):
    """现有 HTTPException 仍由 FastAPI 默认处理器处理（不被兜底处理器覆盖）。"""
    resp = exc_client.get("/_test/http-404")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "找不到该资源"}
