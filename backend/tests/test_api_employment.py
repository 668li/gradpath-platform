# backend/tests/test_api_employment.py
import pytest
from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree


def _seed_employment_data(db_session):
    """创建测试种子数据"""
    school = School(name="清华大学", slug="tsinghua", code="10003")
    db_session.add(school)
    db_session.commit()

    for year in [2023, 2024]:
        report = ReportRecord(
            school_id=school.id, year=year, source_url=f"url-{year}",
            parse_status=ParseStatus.published,
        )
        db_session.add(report)
        db_session.commit()
        db_session.add(EmploymentData(
            report_id=report.id, major="机械工程", degree=Degree.bachelor,
            total_graduates=120, employment_rate=0.45 + (2024 - year) * 0.05,
            further_study_rate=0.35, civil_service_rate=0.10, abroad_rate=0.10,
            employer_ranking=[{"name": "三一重工", "count": 15}, {"name": "比亚迪", "count": 12}],
            industry_distribution={"制造业": 0.4, "互联网": 0.2},
            destination_region={"北京": 0.3, "上海": 0.15},
            school_for_further_study=[{"name": "清华大学", "count": 20}],
        ))
        db_session.commit()

    # 未发布的报告不应出现在搜索结果
    unpublished = ReportRecord(
        school_id=school.id, year=2022, source_url="url-2022",
        parse_status=ParseStatus.parsed,
    )
    db_session.add(unpublished)
    db_session.commit()
    db_session.add(EmploymentData(
        report_id=unpublished.id, major="机械工程", degree=Degree.bachelor,
        total_graduates=100, employment_rate=0.50,
    ))
    db_session.commit()


class TestEmploymentSearch:
    def test_search_by_school_and_major(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        assert resp.status_code == 200
        data = resp.json()
        assert data["school"]["name"] == "清华大学"
        assert "机械" in data["major"]
        assert len(data["records"]) == 2  # 2023 + 2024
        assert data["records"][0]["year"] == 2024  # 降序

    def test_search_with_year_filter(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械&year=2024")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["records"]) == 1
        assert data["records"][0]["year"] == 2024

    def test_search_trend(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        data = resp.json()
        assert "trend" in data
        assert data["trend"]["years"] == [2023, 2024]  # 升序
        assert len(data["trend"]["employment_rate"]) == 2

    def test_search_excludes_unpublished(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=清华&major=机械")
        data = resp.json()
        years = [r["year"] for r in data["records"]]
        assert 2022 not in years  # 未发布的不出现

    def test_search_no_result(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/search?school=不存在&major=机械")
        assert resp.status_code == 200
        data = resp.json()
        assert data["records"] == []
        assert data["school"] is None


class TestEmploymentSchools:
    def test_list_schools(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/schools")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "清华大学"
        assert data[0]["report_count"] == 2  # 只有 published 的


class TestEmploymentStats:
    def test_stats(self, client, db_session):
        _seed_employment_data(db_session)
        resp = client.get("/api/employment/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["school_count"] == 1
        assert data["report_count"] == 2  # 只算 published
        assert data["major_count"] >= 1
