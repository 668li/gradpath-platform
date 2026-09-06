# backend/tests/test_traffic_api.py
"""流量看板 API 测试（admin 鉴权 + 口径换算）。"""

import datetime

import pytest

from app.models.traffic_daily import TrafficDaily
from app.models.user import User


@pytest.fixture
def admin_headers(client, db_session):
    from app.core.security import hash_password

    admin = User(
        email="traffic-admin@test.com",
        password_hash=hash_password("Admin1234!"),
        name="流量管理员",
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    resp = client.post(
        "/api/auth/login",
        json={"email": "traffic-admin@test.com", "password": "Admin1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seed_days(db_session):
    rows = [
        TrafficDaily(
            date=datetime.date(2026, 9, 4),
            pv=100,
            uv=10,
            blocked=5,
            registrations=1,
            human_uv=8,
            human_pv=60,
            machine_uv=1,
            single_uv=1,
        ),
        TrafficDaily(
            date=datetime.date(2026, 9, 5),
            pv=200,
            uv=0,
            blocked=8,
            registrations=0,
            human_uv=0,
            human_pv=0,
            machine_uv=0,
            single_uv=0,
        ),
        TrafficDaily(
            date=datetime.date(2026, 9, 6),
            pv=50,
            uv=5,
            blocked=2,
            registrations=2,
            human_uv=4,
            human_pv=30,
            machine_uv=1,
            single_uv=0,
        ),
    ]
    db_session.add_all(rows)
    db_session.commit()


class TestTrafficDaily:
    def test_requires_auth(self, client):
        assert client.get("/api/traffic/daily").status_code in (401, 403)

    def test_admin_sees_days_sorted_and_conversion(self, client, admin_headers, seed_days):
        resp = client.get("/api/traffic/daily?days=30", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        dates = [d["date"] for d in data["days"]]
        assert dates == sorted(dates)
        by_date = {d["date"]: d for d in data["days"]}
        # uv=0 的日子转化率必须为 0（不许 NaN/除零）
        assert by_date["2026-09-05"]["conversion_rate"] == 0.0
        # 2 注册 / 5 UV = 0.4
        assert abs(by_date["2026-09-06"]["conversion_rate"] - 0.4) < 1e-9
        assert data["summary"]["total_uv"] == 15
        assert data["summary"]["total_registrations"] == 3
        assert data["summary"]["total_human_uv"] == 12
        assert data["summary"]["total_human_pv"] == 90
        assert by_date["2026-09-04"]["machine_uv"] == 1

    def test_days_param_caps_window(self, client, admin_headers, seed_days):
        resp = client.get("/api/traffic/daily?days=2", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.json()["days"]) == 2  # 最近两天：9/5、9/6

    def test_non_admin_forbidden(self, client, db_session):
        from app.core.security import hash_password

        db_session.add(
            User(
                email="pleb@test.com",
                password_hash=hash_password("Pleb1234!"),
                name="普通用户",
                is_admin=False,
            )
        )
        db_session.commit()
        resp = client.post(
            "/api/auth/login",
            json={"email": "pleb@test.com", "password": "Pleb1234!"},
        )
        token = resp.json()["access_token"]
        resp = client.get("/api/traffic/daily", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
