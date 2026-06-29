# backend/tests/test_pipeline_fetcher.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.models.school import School
from app.models.report_record import ReportRecord, ParseStatus
from pipeline.fetcher import fetch_report


SAMPLE_HTML = """
<html><body>
<h1>清华大学2024届毕业生就业质量年度报告</h1>
<table>
<tr><th>专业</th><th>毕业人数</th><th>就业率</th></tr>
<tr><td>机械工程</td><td>120</td><td>45%</td></tr>
</table>
</body></html>
"""


class TestFetcher:
    def test_fetch_html_report(self, db_session):
        """测试成功抓取 HTML 报告"""
        school = School(name="清华大学", slug="tsinghua", report_index_url="https://career.tsinghua.edu.cn/")
        db_session.add(school)
        db_session.commit()

        with patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_HTML
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value = mock_response

            report = fetch_report(db_session, school_slug="tsinghua", year=2024)

        assert report is not None
        assert report.school_id == school.id
        assert report.year == 2024
        assert report.parse_status == ParseStatus.pending
        assert "清华大学2024届" in report.raw_html

    def test_fetch_report_not_found(self, db_session):
        """测试报告链接未找到"""
        school = School(name="清华大学", slug="tsinghua", report_index_url="https://career.tsinghua.edu.cn/")
        db_session.add(school)
        db_session.commit()

        with patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            report = fetch_report(db_session, school_slug="tsinghua", year=2024)

        assert report is not None
        assert report.parse_status == ParseStatus.failed
        assert "404" in (report.parse_error or "")

    def test_fetch_school_not_found(self, db_session):
        """测试学校不存在"""
        report = fetch_report(db_session, school_slug="nonexistent", year=2024)
        assert report is None

    def test_fetch_direct_url(self, db_session):
        """测试直接提供报告 URL"""
        school = School(name="清华大学", slug="tsinghua")
        db_session.add(school)
        db_session.commit()

        with patch("pipeline.fetcher.httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = SAMPLE_HTML
            mock_response.headers = {"content-type": "text/html"}
            mock_get.return_value = mock_response

            report = fetch_report(
                db_session,
                school_slug="tsinghua",
                year=2024,
                direct_url="https://example.com/report.htm",
            )

        assert report is not None
        assert report.source_url == "https://example.com/report.htm"
