# backend/tests/test_api_version_consistency.py
"""API 版本前缀一致性（C3）— 全站统一 /api，旧 /api/v1 路径必须 404。

防止回归：任何人再注册 /api/v1/* 路由或前端再调用 v1 路径都会先挂这里。
"""
import pytest


# 旧 v1 前缀路径（每个后端模块至少抽查一条）
_OLD_V1_PATHS = [
    "/api/v1/actions/today",
    "/api/v1/growth/archive",
    "/api/v1/reviews",
    "/api/v1/admin/sources",
    "/api/v1/admin/research/ingest",
    "/api/v1/admin/ai/governance-status",
    "/api/v1/ai/orchestrate",
]

# 新 /api 路径 → (method, 无鉴权时的期望状态码)
# - 需登录路由：401（未带 token 访问受保护路由）
# - governance-status 为公开诊断端点（前置设计无鉴权依赖）：200
_NEW_API_PATHS = [
    ("GET", "/api/actions/today", 401),
    ("GET", "/api/growth/archive", 401),
    ("GET", "/api/reviews", 401),
    ("GET", "/api/admin/sources", 401),
    ("POST", "/api/admin/research/ingest", 401),
    ("GET", "/api/admin/ai/governance-status", 200),
]


@pytest.mark.parametrize("path", _OLD_V1_PATHS)
def test_old_v1_path_404(client, path):
    resp = client.get(path)
    assert resp.status_code == 404, f"旧 v1 路径不应再注册: {path} → {resp.status_code}"


@pytest.mark.parametrize(("method", "path", "expected"), _NEW_API_PATHS)
def test_new_api_path_registered(client, method, path, expected):
    resp = client.request(method, path, json={"source_system": "x"})
    assert resp.status_code == expected, (
        f"新 /api 路径应已注册（期望 {expected}）: {method} {path} → {resp.status_code}"
    )
