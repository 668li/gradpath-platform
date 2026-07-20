# tests/test_api_grad_visualization.py
"""考研数据可视化 API 测试。"""
from __future__ import annotations

import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


def _make_mock_db():
    db = MagicMock()
    return db


def test_overview_empty_db():
    """空数据库返回 0 统计。"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db

    mock_db = _make_mock_db()
    mock_db.query.return_value.scalar.return_value = 0

    def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        resp = client.get("/api/grad-intel/visualization/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_schools"] == 0
        assert data["total_programs"] == 0
        assert data["average_scoreline"] is None
    finally:
        app.dependency_overrides.clear()


def test_score_trends_empty():
    """院校无数据时返回空趋势。"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db

    mock_db = _make_mock_db()
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []

    def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        resp = client.get(
            "/api/grad-intel/visualization/score-trends",
            params={"university": "北京大学"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["university"] == "北京大学"
        assert data["years"] == []
        assert data["total_score_lines"] == []
    finally:
        app.dependency_overrides.clear()


def test_school_comparison_empty():
    """无院校数据时返回空对比。"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import get_db

    mock_db = _make_mock_db()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    mock_db.query.return_value.filter.return_value.scalar.return_value = 0

    def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        client = TestClient(app)
        resp = client.get(
            "/api/grad-intel/visualization/school-comparison",
            params={"universities": "清华大学,北京大学"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["schools"]) == 2
        assert data["schools"][0]["university_name"] == "清华大学"
        assert data["schools"][1]["university_name"] == "北京大学"
    finally:
        app.dependency_overrides.clear()
