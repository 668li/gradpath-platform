# backend/tests/test_pipeline_extractor.py
import pytest
import json
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from app.models.employment_data import EmploymentData, Degree
from pipeline.extractor import extract_report


SAMPLE_REPORT_HTML = """
<html><body>
<h1>清华大学2024届毕业生就业质量年度报告</h1>
<h2>机械工程</h2>
<p>毕业人数：120人，就业率45%，升学率35%</p>
<table><tr><td>三一重工</td><td>15</td></tr></table>
</body></html>
"""

MOCK_LLM_RESPONSE = json.dumps({
    "majors": [
        {
            "major": "机械工程",
            "degree": "bachelor",
            "total_graduates": 120,
            "employment_rate": 0.45,
            "further_study_rate": 0.35,
            "civil_service_rate": 0.10,
            "abroad_rate": 0.10,
            "startup_rate": 0.0,
            "gap_year_rate": 0.0,
            "employer_ranking": [{"name": "三一重工", "count": 15}],
            "industry_distribution": {"制造业": 0.4, "互联网": 0.2},
            "destination_region": {"北京": 0.3, "上海": 0.15},
            "school_for_further_study": [{"name": "清华大学", "count": 20}]
        }
    ]
})


class TestExtractor:
    def test_extract_success(self, db_session):
        """测试 LLM 解析成功"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=SAMPLE_REPORT_HTML,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        with patch("pipeline.extractor.call_llm", return_value=MOCK_LLM_RESPONSE):
            extract_report(db_session, report_id=report.id)

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.parsed
        assert report.parsed_at is not None

        data = db_session.query(EmploymentData).filter(EmploymentData.report_id == report.id).all()
        assert len(data) == 1
        assert data[0].major == "机械工程"
        assert data[0].employment_rate == 0.45
        assert data[0].employer_ranking == [{"name": "三一重工", "count": 15}]

    def test_extract_llm_failure(self, db_session):
        """测试 LLM 返回无效 JSON"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=SAMPLE_REPORT_HTML,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        with patch("pipeline.extractor.call_llm", return_value="not valid json"):
            extract_report(db_session, report_id=report.id)

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.failed
        assert report.parse_error is not None

    def test_extract_no_html(self, db_session):
        """测试无 raw_html"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()
        report = ReportRecord(
            school_id=school.id,
            year=2024,
            source_url="url",
            raw_html=None,
            parse_status=ParseStatus.pending,
        )
        db_session.add(report)
        db_session.commit()

        result = extract_report(db_session, report_id=report.id)
        assert result is None

        db_session.refresh(report)
        assert report.parse_status == ParseStatus.failed
