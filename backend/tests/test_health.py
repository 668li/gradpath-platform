"""健康检查端点与 CORS 可配置测试（Task 8）。"""
from unittest.mock import MagicMock


def test_health_returns_ok(client):
    """GET /health 始终返回 200 与 status=ok（liveness probe）。"""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_ready_returns_ok_when_db_working(client):
    """GET /ready 在数据库连通时返回 200 与连接状态（readiness probe）。"""
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_ready_returns_503_when_db_unavailable(client):
    """GET /ready 在数据库不可用时返回 503。"""
    from app.database import get_db
    from app.main import app

    def broken_get_db():
        db = MagicMock()
        db.execute.side_effect = RuntimeError("DB down")
        yield db

    app.dependency_overrides[get_db] = broken_get_db
    resp = client.get("/ready")
    assert resp.status_code == 503
    data = resp.json()["detail"]
    assert data["status"] == "not_ready"
    assert data["database"] == "failed"


def test_cors_preflight_returns_allow_origin(client):
    """OPTIONS 预检请求应返回配置允许的 Access-Control-Allow-Origin 头。"""
    resp = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
