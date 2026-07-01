# backend/tests/test_exceptions.py
"""全局异常处理器测试（Task 1）。"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.exceptions import BusinessError, ForbiddenError, NotFoundError
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
        raise BusinessError(detail="自定义业务错误消息")

    def raise_not_found() -> dict:
        raise NotFoundError()

    def raise_forbidden() -> dict:
        raise ForbiddenError()

    def raise_unexpected() -> dict:
        # 故意携带"敏感信息"，验证不会泄露到响应体
        raise RuntimeError("内部敏感信息不应泄露")

    def raise_http_404() -> dict:
        raise HTTPException(status_code=404, detail="找不到该资源")

    routes = {
        "/_test/business": raise_business,
        "/_test/business-custom": raise_business_custom,
        "/_test/not-found": raise_not_found,
        "/_test/forbidden": raise_forbidden,
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
    """BusinessError 默认返回 400 与 detail。"""
    resp = exc_client.get("/_test/business")
    assert resp.status_code == 400
    assert resp.json() == {"detail": "业务错误"}


def test_not_found_error_returns_404(exc_client):
    """NotFoundError 返回 404。"""
    resp = exc_client.get("/_test/not-found")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "资源不存在"}


def test_forbidden_error_returns_403(exc_client):
    """ForbiddenError 返回 403。"""
    resp = exc_client.get("/_test/forbidden")
    assert resp.status_code == 403
    assert resp.json() == {"detail": "无权访问"}


def test_unhandled_exception_returns_500_without_detail(exc_client):
    """未处理异常返回 500 且不泄露内部错误。"""
    resp = exc_client.get("/_test/unexpected")
    assert resp.status_code == 500
    body = resp.json()
    assert body == {"detail": "服务器内部错误"}
    # 确保真正的异常信息没有泄露
    assert "内部敏感信息" not in resp.text


def test_http_exception_still_works(exc_client):
    """现有 HTTPException 仍由 FastAPI 默认处理器处理（不被兜底处理器覆盖）。"""
    resp = exc_client.get("/_test/http-404")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "找不到该资源"}


def test_business_error_with_custom_detail(exc_client):
    """BusinessError 携带自定义 detail 时返回该 detail。"""
    resp = exc_client.get("/_test/business-custom")
    assert resp.status_code == 400
    assert resp.json() == {"detail": "自定义业务错误消息"}
