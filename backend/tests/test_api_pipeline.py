# backend/tests/test_api_pipeline.py
"""Pipeline API 端点测试。"""
import io

import pytest
from app.models.employment_data import Degree, EmploymentData
from app.models.report_record import ParseStatus, ReportRecord
from app.models.school import School
from app.models.user import User


@pytest.fixture
def admin_headers(client, db_session):
    """注册管理员用户并返回认证头。"""
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


@pytest.fixture
def normal_headers(client, db_session):
    """普通用户认证头（非管理员）。"""
    client.post(
        "/api/auth/register",
        json={"email": "normal@test.com", "password": "Test1234!", "name": "普通用户"},
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "normal@test.com", "password": "Test1234!"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_school(db_session) -> School:
    """确保测试数据库中存在一所学校。"""
    school = db_session.query(School).first()
    if not school:
        school = School(name="测试大学", slug="test-uni")
        db_session.add(school)
        db_session.commit()
    return school


class TestPipelineAccess:
    def test_non_admin_blocked(self, client, normal_headers):
        resp = client.get("/api/pipeline/reports", headers=normal_headers)
        assert resp.status_code == 403

    def test_admin_allowed(self, client, admin_headers):
        resp = client.get("/api/pipeline/reports", headers=admin_headers)
        assert resp.status_code == 200


class TestReportList:
    def test_list_reports(self, client, admin_headers):
        resp = client.get("/api/pipeline/reports", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    def test_filter_by_status(self, client, admin_headers, db_session):
        # 构造一份已发布报告
        school = _make_school(db_session)
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="https://example.com",
            parse_status=ParseStatus.published,
        )
        db_session.add(report)
        db_session.commit()

        resp = client.get(
            "/api/pipeline/reports?status=published", headers=admin_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(item["parse_status"] == "published" for item in data["items"])
        assert any(item["year"] == 2024 for item in data["items"])


class TestReportDetail:
    def test_get_report_detail(self, client, admin_headers, db_session):
        school = _make_school(db_session)
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="https://example.com",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()
        emp = EmploymentData(
            report_id=report.id, major="计算机", degree=Degree.bachelor,
            employment_rate=0.5,
        )
        db_session.add(emp)
        db_session.commit()

        resp = client.get(f"/api/pipeline/reports/{report.id}", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(report.id)
        assert "employment_data" in data
        assert data["school_name"] == "测试大学"
        assert len(data["employment_data"]) >= 1


class TestReportDelete:
    def test_delete_report(self, client, admin_headers, db_session):
        school = _make_school(db_session)
        report = ReportRecord(
            school_id=school.id, year=2099, source_url="test",
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()
        resp = client.delete(f"/api/pipeline/reports/{report.id}", headers=admin_headers)
        assert resp.status_code == 204


class TestPublishReport:
    def test_publish_report(self, client, admin_headers, db_session):
        school = _make_school(db_session)
        report = ReportRecord(
            school_id=school.id, year=2098, source_url="test",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()
        resp = client.post(f"/api/pipeline/reports/{report.id}/publish", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.json()["parse_status"] == "published"


class TestIngestURL:
    def test_ingest_url_school_not_found(self, client, admin_headers):
        resp = client.post(
            "/api/pipeline/ingest/url",
            json={"source_type": "crawl", "school_slug": "nonexistent", "year": 2024, "url": "https://example.com"},
            headers=admin_headers,
        )
        assert resp.status_code == 404


class TestStats:
    def test_stats(self, client, admin_headers):
        resp = client.get("/api/pipeline/stats", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_reports" in data
        assert "published_count" in data
        assert "pending_count" in data
        assert "failed_count" in data


class TestFileUpload:
    def test_upload_unsupported_format(self, client, admin_headers):
        resp = client.post(
            "/api/pipeline/ingest/file",
            data={"school_slug": "tsinghua", "year": "2024"},
            files={"file": ("test.txt", io.BytesIO(b"test"), "text/plain")},
            headers=admin_headers,
        )
        assert resp.status_code == 400
