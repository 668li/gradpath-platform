# backend/tests/test_models_employment.py
import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree


class TestSchool:
    def test_create_school(self, db_session):
        school = School(name="清华大学", slug="tsinghua", code="10003")
        db_session.add(school)
        db_session.commit()
        assert school.id is not None
        assert school.name == "清华大学"
        assert school.slug == "tsinghua"

    def test_school_name_unique(self, db_session):
        db_session.add(School(name="清华大学", slug="tsinghua"))
        db_session.commit()
        with pytest.raises(IntegrityError):
            db_session.add(School(name="清华大学", slug="pku"))
            db_session.commit()

    def test_school_slug_unique(self, db_session):
        db_session.add(School(name="清华大学", slug="tsinghua"))
        db_session.commit()
        with pytest.raises(IntegrityError):
            db_session.add(School(name="北京大学", slug="tsinghua"))
            db_session.commit()


class TestReportRecord:
    def test_create_report(self, db_session):
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="https://career.tsinghua.edu.cn/report2024.htm",
        )
        db_session.add(report)
        db_session.commit()
        assert report.id is not None
        assert report.parse_status == ParseStatus.pending

    def test_school_year_unique(self, db_session):
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        db_session.add(ReportRecord(school_id=school.id, year=2024, source_url="url1"))
        db_session.commit()
        with pytest.raises(IntegrityError):
            db_session.add(ReportRecord(school_id=school.id, year=2024, source_url="url2"))
            db_session.commit()


class TestEmploymentData:
    def test_create_employment_data(self, db_session):
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(school_id=school.id, year=2024, source_url="url")
        db_session.add(report)
        db_session.commit()
        data = EmploymentData(
            report_id=report.id,
            major="机械工程",
            degree=Degree.bachelor,
            total_graduates=120,
            employment_rate=0.45,
            further_study_rate=0.35,
            employer_ranking=[{"name": "三一重工", "count": 15}],
            industry_distribution={"制造业": 0.4},
        )
        db_session.add(data)
        db_session.commit()
        assert data.id is not None
        assert data.employer_ranking == [{"name": "三一重工", "count": 15}]

    def test_report_major_degree_unique(self, db_session):
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(school_id=school.id, year=2024, source_url="url")
        db_session.add(report)
        db_session.commit()
        db_session.add(EmploymentData(report_id=report.id, major="机械", degree=Degree.bachelor))
        db_session.commit()
        with pytest.raises(IntegrityError):
            db_session.add(EmploymentData(report_id=report.id, major="机械", degree=Degree.bachelor))
            db_session.commit()
