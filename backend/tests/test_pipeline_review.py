# backend/tests/test_pipeline_review.py
import pytest
from unittest.mock import patch
from io import StringIO

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree
from pipeline.reviewer import review_report, publish_report


class TestReviewer:
    def test_review_accept(self, db_session):
        """测试审核通过"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()
        db_session.add(EmploymentData(
            report_id=report.id, major="机械工程", degree=Degree.bachelor,
            employment_rate=0.45, employer_ranking=[{"name": "三一重工", "count": 15}],
        ))
        db_session.commit()

        with patch("builtins.input", return_value="y"):
            review_report(db_session, report_id=report.id)

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.reviewed

    def test_review_reject(self, db_session):
        """测试审核拒绝"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()

        with patch("builtins.input", return_value="n"):
            review_report(db_session, report_id=report.id)

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.pending

    def test_review_wrong_status(self, db_session):
        """测试非 parsed 状态不能审核"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        result = review_report(db_session, report_id=report.id)
        assert result is None

    def test_publish(self, db_session):
        """测试发布"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.reviewed,
        )
        db_session.add(report)
        db_session.commit()

        publish_report(db_session, report_id=report.id)
        db_session.refresh(report)
        assert report.parse_status == ParseStatus.published

    def test_publish_wrong_status(self, db_session):
        """测试非 reviewed 状态不能发布"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id, year=2024, source_url="url",
            parse_status=ParseStatus.parsed,
        )
        db_session.add(report)
        db_session.commit()

        result = publish_report(db_session, report_id=report.id)
        assert result is None
        db_session.refresh(report)
        assert report.parse_status == ParseStatus.parsed
